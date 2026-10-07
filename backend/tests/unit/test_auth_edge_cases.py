"""Additional edge case tests for AuthService to achieve >=90% test coverage."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import (
    BadRequestException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.security import create_action_token
from app.db.base import Base
from app.models.session import Session
from app.providers.email.smtp import MockEmailProvider
from app.services.auth import AuthService


@pytest.fixture
async def auth_session():
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
async def test_verify_email_edge_cases(auth_session: AsyncSession):
    service = AuthService(auth_session)

    # 1. Invalid token structure
    with pytest.raises(BadRequestException, match="Invalid or expired"):
        await service.verify_email("completely-invalid-token")

    # 2. Token with wrong type
    bad_type_token = create_action_token({"sub": str(uuid.uuid4())}, action="other_action")
    with pytest.raises(BadRequestException, match="Invalid token type"):
        await service.verify_email(bad_type_token)

    # 3. Nonexistent user
    nonexistent_user_token = create_action_token({"sub": str(uuid.uuid4())}, action="verify_email")
    with pytest.raises(NotFoundException, match="User not found"):
        await service.verify_email(nonexistent_user_token)

    # 4. Already verified user
    user = await service.register_user("Zack", "zack@test.com", "ZackStrongPass123!")
    user.email_verified = True
    await auth_session.commit()
    token = create_action_token({"sub": str(user.id)}, action="verify_email")
    assert await service.verify_email(token) is True


@pytest.mark.asyncio
async def test_resend_verification_unverified(auth_session: AsyncSession):
    service = AuthService(auth_session)
    user = await service.register_user("Yara", "yara@test.com", "YaraStrongPass123!")
    assert not user.email_verified
    MockEmailProvider.clear()

    # Resending should deliver an email
    await service.resend_verification("yara@test.com")
    assert len(MockEmailProvider.sent_emails) == 1


@pytest.mark.asyncio
async def test_rotate_refresh_token_edge_cases(auth_session: AsyncSession):
    service = AuthService(auth_session)

    # 1. Nonexistent session token
    with pytest.raises(UnauthorizedException, match="Invalid or expired session"):
        await service.rotate_refresh_token("nonexistent_raw_refresh_token")

    # 2. Expired session token
    user = await service.register_user("Xavier", "xavier@test.com", "XavierPass1234!")
    _, _, refresh = await service.authenticate_user("xavier@test.com", "XavierPass1234!")

    stmt = select(Session).where(Session.user_id == user.id)
    session = (await auth_session.execute(stmt)).scalar_one()
    session.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    await auth_session.commit()

    with pytest.raises(UnauthorizedException, match="Session expired"):
        await service.rotate_refresh_token(refresh)


@pytest.mark.asyncio
async def test_reset_password_edge_cases(auth_session: AsyncSession):
    service = AuthService(auth_session)
    user = await service.register_user("Wendy", "wendy@test.com", "WendyPass1234!")

    # 1. Invalid reset token
    with pytest.raises(BadRequestException, match="Invalid or expired"):
        await service.reset_password("invalid-token", "NewWendyPass2026!")

    # 2. Wrong token type
    wrong_type = create_action_token({"sub": str(user.id)}, action="verify_email")
    with pytest.raises(BadRequestException, match="Invalid token type"):
        await service.reset_password(wrong_type, "NewWendyPass2026!")

    # 3. Nonexistent user
    non_user_token = create_action_token(
        {"sub": str(uuid.uuid4()), "pwd_ver": "fake"}, action="reset_password"
    )
    with pytest.raises(NotFoundException, match="User not found"):
        await service.reset_password(non_user_token, "NewWendyPass2026!")

    # 4. Weak new password
    valid_token = create_action_token(
        {"sub": str(user.id), "pwd_ver": user.password_hash[:10]}, action="reset_password"
    )
    with pytest.raises(BadRequestException, match="at least 8 characters"):
        await service.reset_password(valid_token, "short")


@pytest.mark.asyncio
async def test_revoke_session_not_found(auth_session: AsyncSession):
    service = AuthService(auth_session)
    with pytest.raises(NotFoundException, match="Session not found"):
        await service.revoke_session_by_id(uuid.uuid4(), uuid.uuid4())
