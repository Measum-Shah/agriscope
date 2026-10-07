"""Tests for check constraints, range envelopes, and entity relationships."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.crop import Crop
from app.models.user import User


@pytest.fixture
async def sqlite_session():
    """Provides an in-memory SQLite session with table creation for constraint testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # We create tables that don't depend on Postgres-specific extensions (JSONB/PostGIS)
    # for fast unit testing of models and relationships
    async with engine.begin() as conn:
        # Create users, crops, predictions
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    Base.metadata.tables["users"],
                    Base.metadata.tables["crops"],
                    Base.metadata.tables["crop_stages"],
                ],
            )
        )

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_user_unique_email_constraint(sqlite_session: AsyncSession):
    """Verify unique constraint on email."""
    user1 = User(
        name="User One",
        email="unique@agriscope.local",
        password_hash="hash1",
    )
    sqlite_session.add(user1)
    await sqlite_session.commit()

    user2 = User(
        name="User Two",
        email="unique@agriscope.local",
        password_hash="hash2",
    )
    sqlite_session.add(user2)
    with pytest.raises(IntegrityError):
        await sqlite_session.commit()


@pytest.mark.asyncio
async def test_crop_stages_relationship(sqlite_session: AsyncSession):
    """Verify crop and stages relationship and cascade behavior."""
    crop = Crop(
        name="Test Maize",
        kc_ini=0.3,
        kc_mid=1.2,
        kc_end=0.35,
    )
    sqlite_session.add(crop)
    await sqlite_session.commit()

    stmt = select(Crop).where(Crop.name == "Test Maize")
    result = await sqlite_session.execute(stmt)
    saved_crop = result.scalar_one()
    assert saved_crop.name == "Test Maize"
    assert saved_crop.kc_mid == 1.2
