"""Tests for AccountService: profile, email change, password change, TOTP 2FA, export, deletion."""

from __future__ import annotations

import pyotp
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import BadRequestException, UnauthorizedException
from app.core.security import hash_password
from app.db.base import Base
from app.models.audit_log import AuditLog
from app.models.user import User, UserStatus
from app.providers.email.smtp import MockEmailProvider
from app.services.account import AccountService
from app.services.auth import AuthService


@pytest.fixture
async def account_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    Base.metadata.tables["users"],
                    Base.metadata.tables["sessions"],
                    Base.metadata.tables["audit_logs"],
                ],
            )
        )

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture(autouse=True)
def clean_mock_emails(monkeypatch):
    MockEmailProvider.clear()
    from app.workers.tasks.emails import (
        send_password_reset_email_task,
        send_verification_email_task,
    )

    monkeypatch.setattr(send_verification_email_task, "delay", send_verification_email_task)
    monkeypatch.setattr(send_password_reset_email_task, "delay", send_password_reset_email_task)
    yield
    MockEmailProvider.clear()


@pytest.mark.asyncio
async def test_update_profile(account_session: AsyncSession):
    service = AccountService(account_session)
    user = User(
        name="Original Name",
        email="orig@test.com",
        password_hash=hash_password("Pass1234!"),
    )
    account_session.add(user)
    await account_session.commit()

    updated = await service.update_profile(user, name="Updated Name")
    assert updated.name == "Updated Name"

    # Verify audit log
    stmt = select(AuditLog).where(AuditLog.action == "account.profile_updated")
    audit = (await account_session.execute(stmt)).scalar_one_or_none()
    assert audit is not None


@pytest.mark.asyncio
async def test_email_change_flow(account_session: AsyncSession):
    service = AccountService(account_session)
    user = User(
        name="User EmailChange",
        email="current@test.com",
        password_hash=hash_password("Pass1234!"),
    )
    existing_user = User(
        name="Other User",
        email="taken@test.com",
        password_hash=hash_password("Pass1234!"),
    )
    account_session.add_all([user, existing_user])
    await account_session.commit()

    # Rejection on same email
    with pytest.raises(BadRequestException, match="must be different"):
        await service.request_email_change(user, "current@test.com")

    # Rejection on existing email
    with pytest.raises(BadRequestException, match="already exists"):
        await service.request_email_change(user, "taken@test.com")

    # Successful request
    assert await service.request_email_change(user, "newemail@test.com") is True
    assert len(MockEmailProvider.sent_emails) == 1
    token = MockEmailProvider.sent_emails[0]["text"].split("token=")[1].split()[0].strip()

    # Confirm email change
    updated_user = await service.confirm_email_change(token)
    assert updated_user.email == "newemail@test.com"
    assert updated_user.email_verified is True


@pytest.mark.asyncio
async def test_change_password_and_session_revocation(account_session: AsyncSession):
    auth_service = AuthService(account_session)
    account_service = AccountService(account_session)

    user = await auth_service.register_user("User Pwd", "pwd@test.com", "OldPassword123!")
    _, _, refresh = await auth_service.authenticate_user("pwd@test.com", "OldPassword123!")

    # Verify active session
    sessions_before = await account_service.export_user_data(user)
    assert any(not s.revoked for s in sessions_before["sessions"])

    # Bad current password
    with pytest.raises(BadRequestException, match="Current password is incorrect"):
        await account_service.change_password(user, "WrongPass123!", "NewPassword999!")

    # Weak new password
    with pytest.raises(BadRequestException, match="at least 8 characters"):
        await account_service.change_password(user, "OldPassword123!", "short")

    # Successful change
    assert await account_service.change_password(user, "OldPassword123!", "NewPassword999!") is True

    # Sessions revoked
    sessions_after = await account_service.export_user_data(user)
    assert all(s.revoked for s in sessions_after["sessions"])


@pytest.mark.asyncio
async def test_totp_2fa_full_lifecycle(account_session: AsyncSession):
    account_service = AccountService(account_session)
    auth_service = AuthService(account_session)

    user = await auth_service.register_user("2FA User", "2fa@test.com", "StrongPassword123!")
    assert not user.totp_enabled

    # 1. Setup
    secret, uri, qr_b64 = await account_service.setup_totp(user)
    assert secret is not None
    assert "otpauth://" in uri
    assert len(qr_b64) > 50

    # 2. Verify with wrong code -> fails
    with pytest.raises(BadRequestException, match="Invalid TOTP"):
        await account_service.verify_and_enable_totp(user, "000000")

    # 3. Verify with valid TOTP code
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()
    recovery_codes = await account_service.verify_and_enable_totp(user, valid_code)
    assert len(recovery_codes) == 10
    assert user.totp_enabled is True

    # 4. Login without 2FA code triggers challenge
    with pytest.raises(UnauthorizedException, match="2FA_REQUIRED"):
        await auth_service.authenticate_user("2fa@test.com", "StrongPassword123!")

    # 5. Login with invalid 2FA code fails
    with pytest.raises(UnauthorizedException, match="2FA_REQUIRED"):
        await auth_service.authenticate_user(
            "2fa@test.com", "StrongPassword123!", totp_code="999999"
        )

    # 6. Login with valid TOTP code succeeds
    fresh_code = totp.now()
    u, acc, ref = await auth_service.authenticate_user(
        "2fa@test.com", "StrongPassword123!", totp_code=fresh_code
    )
    assert acc is not None

    # 7. Login with recovery code succeeds and burns the recovery code
    used_recovery = recovery_codes[0]
    u2, acc2, _ = await auth_service.authenticate_user(
        "2fa@test.com", "StrongPassword123!", recovery_code=used_recovery
    )
    assert acc2 is not None

    # Reusing the burned recovery code fails!
    with pytest.raises(UnauthorizedException, match="2FA_REQUIRED"):
        await auth_service.authenticate_user(
            "2fa@test.com", "StrongPassword123!", recovery_code=used_recovery
        )

    # 8. Disable 2FA
    assert await account_service.disable_totp(user, totp.now()) is True
    assert user.totp_enabled is False


@pytest.mark.asyncio
async def test_export_and_deletion(account_session: AsyncSession):
    account_service = AccountService(account_session)
    user = User(
        name="Delete Me",
        email="delete@test.com",
        password_hash=hash_password("Pass1234!"),
        status=UserStatus.ACTIVE.value,
    )
    account_session.add(user)
    await account_session.commit()

    # Export
    data = await account_service.export_user_data(user)
    assert data["user"].email == "delete@test.com"
    assert "exported_at" in data

    # Delete (soft delete)
    assert await account_service.delete_account(user) is True
    assert user.status == UserStatus.SUSPENDED.value
    assert "deleted_" in user.email

    # Audit trail
    logs = await account_service.list_user_audit_logs(user.id)
    assert len(logs) >= 2
