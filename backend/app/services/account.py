"""Account service managing profile updates, email changes, password changes, TOTP 2FA, data export, and deletion."""

from __future__ import annotations

import base64
import io
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pyotp
import qrcode
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    NotFoundException,
)
from app.core.security import (
    create_action_token,
    decode_token,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_password,
)
from app.models.audit_log import AuditLog
from app.models.session import Session
from app.models.user import User, UserStatus
from app.services.audit import AuditService
from app.workers.tasks.emails import send_verification_email_task


class AccountService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_profile(
        self,
        user: User,
        name: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        """Updates user profile information."""
        if name and name.strip():
            user.name = name.strip()
            await self.db.commit()
            await self.db.refresh(user)

            await AuditService.log_event(
                self.db,
                actor=str(user.id),
                action="account.profile_updated",
                target=user.email,
                metadata_json={"name": user.name},
                ip_address=client_ip,
                user_agent=user_agent,
            )
        return user

    async def request_email_change(
        self,
        user: User,
        new_email: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Dispatches an email verification link to the requested new email address."""
        clean_new_email = new_email.strip().lower()
        if clean_new_email == user.email:
            raise BadRequestException(detail="New email must be different from current email.")

        # Check existing user
        stmt = select(User).where(User.email == clean_new_email)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise BadRequestException(detail="An account with this email already exists.")

        token = create_action_token(
            {"sub": str(user.id), "new_email": clean_new_email},
            action="change_email",
            expires_delta=timedelta(hours=24),
        )
        verify_url = f"http://localhost:5173/auth/verify-email?token={token}"

        try:
            send_verification_email_task.delay(clean_new_email, user.name, verify_url)
        except Exception:
            send_verification_email_task(clean_new_email, user.name, verify_url)

        await AuditService.log_event(
            self.db,
            actor=str(user.id),
            action="account.email_change_requested",
            target=clean_new_email,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return True

    async def confirm_email_change(
        self, token: str, client_ip: Optional[str] = None, user_agent: Optional[str] = None
    ) -> User:
        """Confirms email change using the signed token."""
        try:
            payload = decode_token(token)
            if payload.get("type") != "change_email":
                raise BadRequestException(detail="Invalid token type.")
            user_id = uuid.UUID(payload.get("sub"))
            new_email = payload.get("new_email")
        except BadRequestException:
            raise
        except Exception as err:
            raise BadRequestException(detail="Invalid or expired email change token.") from err

        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundException(detail="User not found.")

        old_email = user.email
        user.email = new_email
        user.email_verified = True
        await self.db.commit()
        await self.db.refresh(user)

        await AuditService.log_event(
            self.db,
            actor=str(user.id),
            action="account.email_change_confirmed",
            target=new_email,
            metadata_json={"old_email": old_email, "new_email": new_email},
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return user

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Changes password after verifying current credentials; revokes other sessions."""
        if not verify_password(current_password, user.password_hash):
            await AuditService.log_event(
                self.db,
                actor=str(user.id),
                action="account.password_change_failed_bad_current",
                target=user.email,
                ip_address=client_ip,
                user_agent=user_agent,
            )
            raise BadRequestException(detail="Current password is incorrect.")

        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            raise BadRequestException(detail=error_msg or "Invalid new password.")

        user.password_hash = hash_password(new_password)

        # Invalidate all user sessions
        stmt = update(Session).where(Session.user_id == user.id).values(revoked=True)
        await self.db.execute(stmt)
        await self.db.commit()

        await AuditService.log_event(
            self.db,
            actor=str(user.id),
            action="account.password_changed",
            target=user.email,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return True

    # --- TOTP 2FA Management ---

    async def setup_totp(self, user: User) -> Tuple[str, str, str]:
        """Generates a new TOTP secret and returns (secret, provisioning_uri, qr_code_base64)."""
        secret = pyotp.random_base32()
        user.totp_secret = secret
        await self.db.commit()

        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name="AgriScope")

        # Generate QR code
        qr = qrcode.QRCode(box_size=4, border=2)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return secret, provisioning_uri, qr_code_base64

    async def verify_and_enable_totp(
        self,
        user: User,
        code: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> List[str]:
        """Verifies code against pending totp_secret, enables 2FA, and returns 10 single-use recovery codes."""
        if not user.totp_secret:
            raise BadRequestException(detail="TOTP setup has not been initiated.")

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code):
            raise BadRequestException(detail="Invalid TOTP authentication code.")

        # Generate 10 plaintext recovery codes
        raw_recovery_codes = [secrets.token_hex(4).upper() for _ in range(10)]
        # Store hashed recovery codes
        hashed_codes = [hash_token(rc) for rc in raw_recovery_codes]

        user.totp_enabled = True
        user.totp_recovery_codes = hashed_codes
        await self.db.commit()

        await AuditService.log_event(
            self.db,
            actor=str(user.id),
            action="account.totp_enabled",
            target=user.email,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return raw_recovery_codes

    async def disable_totp(
        self,
        user: User,
        code: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Disables TOTP 2FA upon code verification."""
        if not user.totp_enabled or not user.totp_secret:
            raise BadRequestException(detail="2FA is not enabled.")

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code):
            raise BadRequestException(detail="Invalid TOTP code.")

        user.totp_enabled = False
        user.totp_secret = None
        user.totp_recovery_codes = []
        await self.db.commit()

        await AuditService.log_event(
            self.db,
            actor=str(user.id),
            action="account.totp_disabled",
            target=user.email,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return True

    async def verify_totp_or_recovery_code(
        self,
        user: User,
        code: Optional[str] = None,
        recovery_code: Optional[str] = None,
    ) -> bool:
        """Validates either an active TOTP 6-digit code or burns a single-use recovery code."""
        if not user.totp_enabled:
            return True

        if code and user.totp_secret:
            totp = pyotp.TOTP(user.totp_secret)
            if totp.verify(code):
                return True

        if recovery_code:
            clean_rec = recovery_code.strip().upper()
            hashed_rec = hash_token(clean_rec)
            existing_codes = list(user.totp_recovery_codes or [])
            if hashed_rec in existing_codes:
                # Burn code
                existing_codes.remove(hashed_rec)
                user.totp_recovery_codes = existing_codes
                await self.db.commit()
                return True

        return False

    # --- Self-Service Data Export & Deletion ---

    async def export_user_data(self, user: User) -> Dict[str, Any]:
        """Collects user profile, sessions, and audit events for GDPR/self-service export."""
        sessions_stmt = select(Session).where(Session.user_id == user.id)
        sessions = (await self.db.execute(sessions_stmt)).scalars().all()

        audit_stmt = select(AuditLog).where(AuditLog.actor == str(user.id))
        audit_events = (await self.db.execute(audit_stmt)).scalars().all()

        await AuditService.log_event(
            self.db,
            actor=str(user.id),
            action="account.data_exported",
            target=user.email,
        )

        return {
            "user": user,
            "sessions": sessions,
            "audit_events": audit_events,
            "exported_at": datetime.now(timezone.utc),
        }

    async def delete_account(
        self,
        user: User,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Soft-deletes the user account, marks status as suspended, and revokes all sessions."""
        user.status = UserStatus.SUSPENDED.value
        user.email = f"deleted_{user.id}_{user.email}"

        # Revoke all sessions
        stmt = update(Session).where(Session.user_id == user.id).values(revoked=True)
        await self.db.execute(stmt)
        await self.db.commit()

        await AuditService.log_event(
            self.db,
            actor=str(user.id),
            action="account.deleted_soft",
            target=user.email,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return True

    async def list_user_audit_logs(self, user_id: uuid.UUID) -> List[AuditLog]:
        """Retrieves audit trail events where the caller was the actor."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.actor == str(user_id))
            .order_by(AuditLog.timestamp.desc())
            .limit(100)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
