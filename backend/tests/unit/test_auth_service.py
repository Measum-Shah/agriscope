"""Comprehensive tests for AuthService: registration, email verification, lockout,
token rotation, reuse detection, password reset, rate limits, and audit logs.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import (
    BadRequestException,
    UnauthorizedException,
)
from app.db.base import Base
from app.models.audit_log import AuditLog
from app.models.user import User
from app.providers.email.smtp import MockEmailProvider
from app.services.auth import AuthService


@pytest.fixture
async def auth_session():
    """Provides an isolated database session with required auth tables."""
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
    # Mock celery tasks to run directly in tests without redis wait
    from app.workers.tasks.emails import (
        send_password_reset_email_task,
        send_verification_email_task,
    )

    monkeypatch.setattr(send_verification_email_task, "delay", send_verification_email_task)
    monkeypatch.setattr(send_password_reset_email_task, "delay", send_password_reset_email_task)
    yield
    MockEmailProvider.clear()


@pytest.mark.asyncio
async def test_register_password_complexity_and_duplicate(auth_session: AsyncSession):
    service = AuthService(auth_session)

    # 1. Short password failure
    with pytest.raises(BadRequestException, match="at least 8 characters"):
        await service.register_user("Alice", "alice@test.com", "Short1")

    # 2. No uppercase failure
    with pytest.raises(BadRequestException, match="uppercase"):
        await service.register_user("Alice", "alice@test.com", "nouppercase123")

    # 3. No digit failure
    with pytest.raises(BadRequestException, match="digit"):
        await service.register_user("Alice", "alice@test.com", "NoDigitsHere!")

    # 4. Common breached password
    with pytest.raises(BadRequestException, match="too common or compromised"):
        await service.register_user("Alice", "alice@test.com", "Password123")

    # 5. Success
    user = await service.register_user("Alice", "alice@test.com", "SecurePass123!")
    assert user.id is not None
    assert user.email == "alice@test.com"
    assert not user.email_verified
    assert len(MockEmailProvider.sent_emails) == 1
    assert "Verify your AgriScope Account" in MockEmailProvider.sent_emails[0]["subject"]

    # 6. Duplicate registration failure
    with pytest.raises(BadRequestException, match="already exists"):
        await service.register_user("Alice Duplicate", "alice@test.com", "SecurePass123!")


@pytest.mark.asyncio
async def test_email_verification_and_resend(auth_session: AsyncSession):
    service = AuthService(auth_session)
    user = await service.register_user("Bob", "bob@test.com", "BobSecretPassword123")
    assert not user.email_verified

    # Extract token from mock email
    email_text = MockEmailProvider.sent_emails[0]["text"]
    token = email_text.split("token=")[1].split()[0].strip()

    # Verify email
    res = await service.verify_email(token)
    assert res is True
    await auth_session.refresh(user)
    assert user.email_verified is True

    # Resend verification
    MockEmailProvider.clear()
    await service.resend_verification("bob@test.com")
    # Already verified, so no new email
    assert len(MockEmailProvider.sent_emails) == 0

    # Resend for unregistered email shouldn't leak or error
    await service.resend_verification("nonexistent@test.com")
    assert len(MockEmailProvider.sent_emails) == 0


@pytest.mark.asyncio
async def test_login_success_and_last_login(auth_session: AsyncSession):
    service = AuthService(auth_session)
    await service.register_user("Carol", "carol@test.com", "CarolPassword999")

    user, access_token, refresh_token = await service.authenticate_user(
        "carol@test.com", "CarolPassword999", client_ip="127.0.0.1", user_agent="Pytest"
    )
    assert access_token is not None
    assert refresh_token is not None
    assert user.last_login is not None
    assert user.failed_attempts == 0

    # Check session created
    sessions = await service.list_sessions(user.id)
    assert len(sessions) == 1
    assert not sessions[0].revoked


@pytest.mark.asyncio
async def test_enumeration_resistance_bad_credentials(auth_session: AsyncSession):
    service = AuthService(auth_session)
    # Non-existent user
    with pytest.raises(UnauthorizedException, match="Invalid email or password"):
        await service.authenticate_user("ghost@test.com", "WrongPassword123")

    # Audit log check
    stmt = select(AuditLog).where(AuditLog.action == "auth.login_failed_not_found")
    res = await auth_session.execute(stmt)
    assert res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_lockout_and_auto_unlock(auth_session: AsyncSession):
    service = AuthService(auth_session)
    await service.register_user("Dave", "dave@test.com", "DaveSecurePassword88")

    initial_time = datetime(2026, 10, 7, 12, 0, 0, tzinfo=timezone.utc)
    with freeze_time(initial_time):
        # 4 consecutive bad attempts
        for _ in range(4):
            with pytest.raises(UnauthorizedException, match="Invalid email or password"):
                await service.authenticate_user("dave@test.com", "BadPassword123")

        user_stmt = select(User).where(User.email == "dave@test.com")
        user = (await auth_session.execute(user_stmt)).scalar_one()
        assert user.failed_attempts == 4
        assert user.locked_until is None

        # 5th bad attempt -> lockout
        with pytest.raises(UnauthorizedException, match="Invalid email or password"):
            await service.authenticate_user("dave@test.com", "BadPassword123")

        await auth_session.refresh(user)
        assert user.failed_attempts == 5
        assert user.locked_until is not None

        # 6th attempt while locked -> blocked
        with pytest.raises(UnauthorizedException, match="Account is temporarily locked"):
            await service.authenticate_user("dave@test.com", "DaveSecurePassword88")

    # Fast-forward 16 minutes -> auto-unlock
    unlocked_time = initial_time + timedelta(minutes=16)
    with freeze_time(unlocked_time):
        authed_user, access, refresh = await service.authenticate_user(
            "dave@test.com", "DaveSecurePassword88"
        )
        assert authed_user.failed_attempts == 0
        assert authed_user.locked_until is None
        assert access is not None


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_reuse_detection(auth_session: AsyncSession):
    service = AuthService(auth_session)
    await service.register_user("Eve", "eve@test.com", "EvePassword777")

    user, access1, refresh1 = await service.authenticate_user("eve@test.com", "EvePassword777")

    # Rotate once: refresh1 -> refresh2
    user, access2, refresh2 = await service.rotate_refresh_token(refresh1)
    assert refresh2 != refresh1
    assert access2 != access1

    # Attacker tries to reuse refresh1 -> should trigger reuse detection and revoke whole family!
    with pytest.raises(UnauthorizedException, match="Session compromised"):
        await service.rotate_refresh_token(refresh1)

    # Legitimate refresh2 should now also be revoked due to family revocation!
    with pytest.raises(UnauthorizedException, match="Session compromised"):
        await service.rotate_refresh_token(refresh2)

    # Check audit log
    stmt = select(AuditLog).where(AuditLog.action == "auth.token_reuse_detected")
    audit_list = (await auth_session.execute(stmt)).scalars().all()
    assert len(audit_list) >= 1


@pytest.mark.asyncio
async def test_password_reset_flow_and_session_invalidation(auth_session: AsyncSession):
    service = AuthService(auth_session)
    user = await service.register_user("Frank", "frank@test.com", "FrankInitialPassword1")

    # Login and verify session exists
    _, _, refresh = await service.authenticate_user("frank@test.com", "FrankInitialPassword1")
    sessions = await service.list_sessions(user.id)
    assert any(not s.revoked for s in sessions)

    # Request password reset
    MockEmailProvider.clear()
    await service.request_password_reset("frank@test.com")
    assert len(MockEmailProvider.sent_emails) == 1
    reset_email = MockEmailProvider.sent_emails[0]
    token = reset_email["text"].split("token=")[1].split()[0].strip()

    # Reset password
    res = await service.reset_password(token, "BrandNewFrankPass2026!")
    assert res is True

    # Old password no longer works
    with pytest.raises(UnauthorizedException):
        await service.authenticate_user("frank@test.com", "FrankInitialPassword1")

    # New password works
    user, _, _ = await service.authenticate_user("frank@test.com", "BrandNewFrankPass2026!")
    assert user is not None

    # Reset token cannot be reused
    with pytest.raises(BadRequestException, match="already been used"):
        await service.reset_password(token, "AnotherPassword123")


@pytest.mark.asyncio
async def test_logout_and_revoke_session(auth_session: AsyncSession):
    service = AuthService(auth_session)
    user = await service.register_user("Grace", "grace@test.com", "GraceSecretPass10")
    _, _, refresh = await service.authenticate_user("grace@test.com", "GraceSecretPass10")

    sessions = await service.list_sessions(user.id)
    assert len(sessions) == 1

    # Revoke session by id
    await service.revoke_session_by_id(user.id, sessions[0].id)
    sessions_after = await service.list_sessions(user.id)
    assert sessions_after[0].revoked is True

    # Logout
    await service.logout(refresh)
    # Logout all
    await service.logout_all(user.id)
