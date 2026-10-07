"""Celery tasks for scheduled satellite analysis and NDVI delta notifications."""

import asyncio
from datetime import date, timedelta
from app.workers.celery_app import celery_app
from app.core.logging import logger


@celery_app.task(name="app.workers.tasks.satellite.refresh_active_fields_weekly")
def refresh_active_fields_weekly() -> dict:
    """Weekly Celery Beat task refreshing Sentinel-2 imagery for active fields."""
    logger.info("Executing scheduled weekly satellite analysis for active fields...")

    async def _async_refresh():
        from app.db.session import async_session_factory
        from app.models.field import Field
        from app.services.remote_sensing_service import RemoteSensingService
        from sqlalchemy import select

        updated_count = 0
        async with async_session_factory() as session:
            stmt = select(Field)
            res = await session.execute(stmt)
            fields = res.scalars().all()
            service = RemoteSensingService(session)

            for field_obj in fields:
                try:
                    await service.analyze_field(
                        user=field_obj.user,
                        field_id=field_obj.id,
                        start_date=date.today() - timedelta(days=14),
                        end_date=date.today(),
                    )
                    updated_count += 1
                except Exception as e:
                    logger.warning(f"Weekly analysis failed for field {field_obj.id}: {e}")

        return {"fields_refreshed": updated_count}

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_async_refresh())
