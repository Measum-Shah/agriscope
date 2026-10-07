"""Authentication service handling registration, login, token rotation, lockout, and password recovery."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    create_action_token,
    decode_token,
    generate_secure_token,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_password,
)
from app.models.session import Session
from app.models.user import User, UserPlan, UserRole, UserStatus
from app.services.audit import AuditService
from app.workers.tasks.emails import (
    send_password_reset_email_task,
    send_verification_email_task,
)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(
        self,
        name: str,
        email: str,
        password: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        """Registers a new user after enforcing password complexity and sends verification token."""
        clean_email = email.strip().lower()

        # Enforce password strength
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            raise BadRequestException(detail=error_msg or "Invalid password")

        # Check existing user
        stmt = select(User).where(User.email == clean_email)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            # Audit registration collision
            await AuditService.log_event(
                self.db,
                actor=clean_email,
                action="auth.register_failed_duplicate",
                target=clean_email,
                ip_address=client_ip,
                user_agent=user_agent,
            )
            raise BadRequestException(detail="An account with this email already exists.")

        user = User(
            name=name.strip(),
            email=clean_email,
            password_hash=hash_password(password),
            role=UserRole.FREE.value,
            plan=UserPlan.FREE.value,
            status=UserStatus.ACTIVE.value,
            email_verified=False,
            failed_attempts=0,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        # Generate verification token (24h)
        verify_token = create_action_token(
            {"sub": str(user.id), "email": user.email},
            action="verify_email",
            expires_delta=timedelta(hours=24),
        )
        verify_url = f"http://localhost:5173/auth/verify-email?token={verify_token}"

        # Dispatch async email task
        try:
            send_verification_email_task.delay(user.email, user.name, verify_url)
        except Exception as e:
            logger.warning(
                f"Could not queue Celery verification email, falling back to direct send: {e}"
            )
            from app.workers.tasks.emails import send_verification_email_task as direct_task

            direct_task(user.email, user.name, verify_url)

        await AuditService.log_event(
            self.db,
            actor=str(user.id),
            action="auth.register_success",
            target=user.email,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return user

    async def verify_email(
        self, token: str, client_ip: Optional[str] = None, user_agent: Optional[str] = None
    ) -> bool:
        """Verifies user email from single-use token."""
        try:
            payload = decode_token(token)
            if payload.get("type") != "verify_email":
                raise BadRequestException(detail="Invalid token type for email verification.")
            user_id = uuid.UUID(payload.get("sub"))
        except BadRequestException:
            raise
        except Exception as err:
            raise BadRequestException(detail="Invalid or expired verification token.") from err

        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundException(detail="User not found.")

        if user.email_verified:
            return True

        user.email_verified = True
        await self.db.commit()

        await AuditService.log_event(
            self.db,
            actor=str(user.id),
            action="auth.verify_email_success",
            target=user.email,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return True

    async def resend_verification(
        self, email: str, client_ip: Optional[str] = None, user_agent: Optional[str] = None
    ) -> bool:
        """Resends verification email without leaking user existence."""
        clean_email = email.strip().lower()
        stmt = select(User).where(User.email == clean_email)
        user = (await self.db.execute(stmt)).scalar_one_or_none()

        if user and not user.email_verified:
            verify_token = create_action_token(
                {"sub": str(user.id), "email": user.email},
                action="verify_email",
                expires_delta=timedelta(hours=24),
            )
            verify_url = f"http://localhost:5173/auth/verify-email?token={verify_token}"
            try:
                send_verification_email_task.delay(user.email, user.name, verify_url)
            except Exception:
                from app.workers.tasks.emails import send_verification_email_task as direct_task

                direct_task(user.email, user.name, verify_url)

            await AuditService.log_event(
                self.db,
                actor=str(user.id),
                action="auth.resend_verification",
                target=user.email,
                ip_address=client_ip,
                user_agent=user_agent,
            )
        return True

    async def authenticate_user(
        self,
        email: str,
        password: str,
        totp_code: Optional[str] = None,
        recovery_code: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[User, str, str]:
        """Authenticates user with lockout protection (5 failed attempts -> 15 min lock).

        Returns: (user, access_token, raw_refresh_token)
        """
        clean_email = email.strip().lower()
        now = datetime.now(timezone.utc)

        stmt = select(User).where(User.email == clean_email)
        user = (await self.db.execute(stmt)).scalar_one_or_none()

        # Constant-time mitigation against enumeration
        dummy_hash = "$2b$12$K1JjJ5aU6bZ3P5Vd7PjZde4m2i9A1q.C5iJ4bK0O8d1s9x7m3k9mO"

        if not user:
            verify_password(password, dummy_hash)
            await AuditService.log_event(
                self.db,
                actor=clean_email,
                action="auth.login_failed_not_found",
                target=clean_email,
                ip_address=client_ip,
                user_agent=user_agent,
            )
            raise UnauthorizedException(detail="Invalid email or password.")

        # Check account lockout
        if user.locked_until:
            locked_until = (
                user.locked_until
                if user.locked_until.tzinfo
                else user.locked_until.replace(tzinfo=timezone.utc)
            )
            if locked_until > now:
                minutes_left = max(1, int((locked_until - now).total_seconds() / 60))
                await AuditService.log_event(
                    self.db,
                    actor=str(user.id),
                    action="auth.login_blocked_locked",
                    target=user.email,
                    ip_address=client_ip,
                    user_agent=user_agent,
                )
                raise UnauthorizedException(
                    detail=f"Account is temporarily locked. Please try again in {minutes_left} minutes."
                )

        # Check password
        if not verify_password(password, user.password_hash):
            user.failed_attempts += 1
            if user.failed_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = now + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
                logger.warning(f"User {user.email} locked out until {user.locked_until}")
            await self.db.commit()

            await AuditService.log_event(
                self.db,
                actor=str(user.id),
                action="auth.login_failed_bad_password",
                target=user.email,
                metadata_json={"failed_attempts": user.failed_attempts},
                ip_address=client_ip,
                user_agent=user_agent,
            )
            raise UnauthorizedException(detail="Invalid email or password.")

        # Successful login: reset lockout
        user.failed_attempts = 0
        user.locked_until = None
        user.last_login = now

        # If 2FA enabled, check code or recovery code
        if user.totp_enabled:
            # We check if 2FA code is verified
            from app.services.account import AccountService

            acc_service = AccountService(self.db)
            is_2fa_valid = await acc_service.verify_totp_or_recovery_code(
                user=user, code=totp_code, recovery_code=recovery_code
            )
            if not is_2fa_valid:
                temp_token = create_action_token(
                    {"sub": str(user.id), "email": user.email},
                    action="2fa_challenge",
                    expires_delta=timedelta(minutes=5),
                )
                raise UnauthorizedException(detail="2FA_REQUIRED:" + temp_token)

        # Create session with rotating token family
        raw_refresh_token = generate_secure_token(48)
        hashed_refresh = hash_token(raw_refresh_token)
        family_id = uuid.uuid4()
        session_expires = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        new_session = Session(
            user_id=user.id,
            token_family=family_id,
            hashed_token=hashed_refresh,
            ip_address=client_ip,
            user_agent=user_agent,
            expires_at=session_expires,
            revoked=False,
            reuse_detected=False,
        )
        self.db.add(new_session)
        await self.db.commit()
        await self.db.refresh(user)

        # Access token
        access_token = create_access_token(
            {"sub": str(user.id), "role": user.role, "plan": user.plan}
        )

        await AuditService.log_event(
            self.db,
            actor=str(user.id),
            action="auth.login_success",
            target=user.email,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return user, access_token, raw_refresh_token

    async def rotate_refresh_token(
        self,
        raw_refresh_token: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[User, str, str]:
        """Rotates refresh token. Detects token reuse and revokes entire family if reuse occurs."""
        hashed_refresh = hash_token(raw_refresh_token)
        now = datetime.now(timezone.utc)

        stmt = select(Session).where(Session.hashed_token == hashed_refresh)
        session = (await self.db.execute(stmt)).scalar_one_or_none()

        if not session:
            raise UnauthorizedException(detail="Invalid or expired session.")

        # Check for token reuse on revoked session
        if session.revoked:
            logger.warning(
                f"[SECURITY ALERT] Refresh token reuse detected for family {session.token_family}! Revoking entire family."
            )
            # Invalidate all sessions in this family
            revoke_stmt = (
                update(Session)
                .where(Session.token_family == session.token_family)
                .values(revoked=True, reuse_detected=True)
            )
            await self.db.execute(revoke_stmt)
            await self.db.commit()

            await AuditService.log_event(
                self.db,
                actor=str(session.user_id),
                action="auth.token_reuse_detected",
                target=str(session.token_family),
                ip_address=client_ip,
                user_agent=user_agent,
            )
            raise UnauthorizedException(detail="Session compromised. Please login again.")

        session_expires = (
            session.expires_at
            if session.expires_at.tzinfo
            else session.expires_at.replace(tzinfo=timezone.utc)
        )
        if session_expires < now:
            session.revoked = True
            await self.db.commit()
            raise UnauthorizedException(detail="Session expired. Please login again.")

        # Revoke current token
        session.revoked = True

        # Issue new token in same family
        new_raw_refresh = generate_secure_token(48)
        new_hashed = hash_token(new_raw_refresh)
        new_session = Session(
            user_id=session.user_id,
            token_family=session.token_family,
            hashed_token=new_hashed,
            ip_address=client_ip,
            user_agent=user_agent,
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            revoked=False,
            reuse_detected=False,
        )
        self.db.add(new_session)
        await self.db.commit()

        user = await self.db.get(User, session.user_id)
        if not user:
            raise UnauthorizedException(detail="User no longer exists.")

        new_access_token = create_access_token(
            {"sub": str(user.id), "role": user.role, "plan": user.plan}
        )

        await AuditService.log_event(
            self.db,
            actor=str(user.id),
            action="auth.refresh_token_rotated",
            target=str(session.token_family),
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return user, new_access_token, new_raw_refresh

    async def logout(self, raw_refresh_token: str) -> None:
        """Revokes specific session token."""
        hashed = hash_token(raw_refresh_token)
        stmt = select(Session).where(Session.hashed_token == hashed)
        session = (await self.db.execute(stmt)).scalar_one_or_none()
        if session:
            session.revoked = True
            await self.db.commit()
            await AuditService.log_event(
                self.db,
                actor=str(session.user_id),
                action="auth.logout",
                target=str(session.id),
            )

    async def logout_all(self, user_id: uuid.UUID) -> None:
        """Revokes all active sessions for a user."""
        stmt = update(Session).where(Session.user_id == user_id).values(revoked=True)
        await self.db.execute(stmt)
        await self.db.commit()
        await AuditService.log_event(
            self.db,
            actor=str(user_id),
            action="auth.logout_all",
            target=str(user_id),
        )

    async def list_sessions(self, user_id: uuid.UUID) -> List[Session]:
        """Lists active and past sessions for the user."""
        stmt = select(Session).where(Session.user_id == user_id).order_by(Session.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def revoke_session_by_id(self, user_id: uuid.UUID, session_id: uuid.UUID) -> bool:
        """Revokes a specific session belonging to user."""
        session = await self.db.get(Session, session_id)
        if not session or session.user_id != user_id:
            raise NotFoundException(detail="Session not found.")
        session.revoked = True
        await self.db.commit()
        await AuditService.log_event(
            self.db,
            actor=str(user_id),
            action="auth.revoke_session",
            target=str(session_id),
        )
        return True

    async def request_password_reset(
        self, email: str, client_ip: Optional[str] = None, user_agent: Optional[str] = None
    ) -> bool:
        """Initiates password reset with 1h single-use token without revealing user existence."""
        clean_email = email.strip().lower()
        stmt = select(User).where(User.email == clean_email)
        user = (await self.db.execute(stmt)).scalar_one_or_none()

        if user:
            reset_token = create_action_token(
                {"sub": str(user.id), "email": user.email, "pwd_ver": user.password_hash[:10]},
                action="reset_password",
                expires_delta=timedelta(hours=1),
            )
            reset_url = f"http://localhost:5173/auth/reset-password?token={reset_token}"
            try:
                send_password_reset_email_task.delay(user.email, user.name, reset_url)
            except Exception:
                from app.workers.tasks.emails import send_password_reset_email_task as direct_task

                direct_task(user.email, user.name, reset_url)

            await AuditService.log_event(
                self.db,
                actor=str(user.id),
                action="auth.request_password_reset",
                target=user.email,
                ip_address=client_ip,
                user_agent=user_agent,
            )
        return True

    async def reset_password(
        self,
        token: str,
        new_password: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Resets password, invalidating token and revoking all user sessions."""
        try:
            payload = decode_token(token)
            if payload.get("type") != "reset_password":
                raise BadRequestException(detail="Invalid token type.")
            user_id = uuid.UUID(payload.get("sub"))
            pwd_ver = payload.get("pwd_ver")
        except BadRequestException:
            raise
        except Exception as err:
            raise BadRequestException(detail="Invalid or expired reset token.") from err

        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundException(detail="User not found.")

        # Ensure single-use: token is tied to password prefix
        if user.password_hash[:10] != pwd_ver:
            raise BadRequestException(detail="Password reset token has already been used.")

        # Validate new password complexity
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            raise BadRequestException(detail=error_msg or "Invalid password")

        # Update password
        user.password_hash = hash_password(new_password)
        user.failed_attempts = 0
        user.locked_until = None

        # Revoke all sessions
        await self.logout_all(user.id)
        await self.db.commit()

        await AuditService.log_event(
            self.db,
            actor=str(user.id),
            action="auth.reset_password_success",
            target=user.email,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return True
