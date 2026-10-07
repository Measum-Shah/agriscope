"""Database initialization and seeding script for AgriScope.
Loads all FAO-56 crops and initializes default admin user idempotently.
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import async_session_factory, engine
from app.models.crop import Crop, CropStage
from app.models.user import User, UserPlan, UserRole, UserStatus
from app.services.model_registry_sync import sync_models_to_database


async def seed_admin(session: AsyncSession) -> None:
    """Ensures default admin user exists."""
    admin_email = "admin@agriscope.local"
    stmt = select(User).where(User.email == admin_email)
    result = await session.execute(stmt)
    existing_admin = result.scalar_one_or_none()

    if existing_admin is None:
        logger.info(f"Creating default admin user ({admin_email})...")
        admin = User(
            name="AgriScope Administrator",
            email=admin_email,
            password_hash=hash_password("admin_agriscope_secret_2026"),
            role=UserRole.ADMIN.value,
            plan=UserPlan.ADMIN.value,
            status=UserStatus.ACTIVE.value,
            email_verified=True,
            totp_enabled=False,
        )
        session.add(admin)
        await session.commit()
        logger.info("Admin user created successfully.")
    else:
        logger.info("Admin user already exists. Skipping.")


async def seed_crops(session: AsyncSession) -> None:
    """Loads crops and growth stages from seeds/crops.json idempotently."""
    seeds_file = Path(__file__).parent / "seeds" / "crops.json"
    if not seeds_file.exists():
        logger.warning(f"Seeds file not found at {seeds_file}")
        return

    with open(seeds_file, "r", encoding="utf-8") as f:
        crops_data = json.load(f)

    logger.info(f"Checking and seeding {len(crops_data)} crops...")
    for crop_dict in crops_data:
        crop_name = crop_dict["name"]
        stmt = select(Crop).where(Crop.name == crop_name)
        result = await session.execute(stmt)
        existing_crop = result.scalar_one_or_none()

        if existing_crop is None:
            new_crop = Crop(
                name=crop_name,
                scientific_name=crop_dict.get("scientific_name"),
                kc_ini=float(crop_dict["kc_ini"]),
                kc_mid=float(crop_dict["kc_mid"]),
                kc_end=float(crop_dict["kc_end"]),
                description=f"FAO-56 reference parameters for {crop_name}",
            )
            session.add(new_crop)
            await session.flush()

            # Add stages
            growth_stages = crop_dict.get("growth_stages_days", {})
            for stage_name, days in growth_stages.items():
                stage = CropStage(
                    crop_id=new_crop.id,
                    stage_name=stage_name,
                    duration_days=int(days),
                )
                session.add(stage)
            logger.info(f"Added crop: {crop_name}")

    await session.commit()
    logger.info("Crop seeding complete.")


async def init_db() -> None:
    """Creates database tables and executes idempotent seeds."""
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        await seed_admin(session)
        await seed_crops(session)
        await sync_models_to_database(session)
    logger.info("Database initialization and seeding finished.")


if __name__ == "__main__":
    asyncio.run(init_db())
