"""Tests for db seed idempotency."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.init_db import seed_admin, seed_crops
from app.models.crop import Crop
from app.models.user import User


@pytest.fixture
async def seed_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
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
async def test_seed_admin_and_crops_idempotent(seed_session: AsyncSession):
    """Running seed multiple times does not duplicate admin user or crops."""
    # First run
    await seed_admin(seed_session)
    await seed_crops(seed_session)

    # Check counts
    res_admin = await seed_session.execute(select(User))
    users_first = res_admin.scalars().all()
    assert len(users_first) == 1
    assert users_first[0].email == "admin@agriscope.local"

    res_crops = await seed_session.execute(select(Crop))
    crops_first = res_crops.scalars().all()
    assert len(crops_first) >= 20  # 20 FAO-56 crops loaded

    # Second run
    await seed_admin(seed_session)
    await seed_crops(seed_session)

    res_admin2 = await seed_session.execute(select(User))
    users_second = res_admin2.scalars().all()
    assert len(users_second) == 1

    res_crops2 = await seed_session.execute(select(Crop))
    crops_second = res_crops2.scalars().all()
    assert len(crops_second) == len(crops_first)
