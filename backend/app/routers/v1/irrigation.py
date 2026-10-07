"""Irrigation management and daily soil water balance API router."""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.irrigation import (
    FieldIrrigationPlanResponse,
    IrrigationEventCreate,
    IrrigationEventResponse,
)
from app.services.irrigation_service import IrrigationService

router = APIRouter(prefix="/irrigation", tags=["Irrigation"])


@router.get("/plan/{field_id}", response_model=FieldIrrigationPlanResponse)
async def get_field_irrigation_plan(
    field_id: uuid.UUID,
    soil_type: str = Query("loam", description="Soil texture preset (sand, loam, clay, etc.)"),
    mad_fraction: float = Query(0.5, ge=0.1, le=0.9, description="Management Allowed Depletion fraction"),
    forecast_days: int = Query(7, ge=1, le=14, description="Days to forecast forward"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Calculate dynamic soil water balance, root zone depletion, and forecast irrigation schedule."""
    service = IrrigationService(db)
    return await service.calculate_field_irrigation_plan(
        field_id=field_id,
        user=current_user,
        soil_type=soil_type,
        mad_fraction=mad_fraction,
        forecast_days=forecast_days,
    )


@router.get("/events/{field_id}", response_model=List[IrrigationEventResponse])
async def list_irrigation_events(
    field_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all applied irrigation events logged for a specific field."""
    service = IrrigationService(db)
    return await service.get_field_events(field_id, current_user)


@router.post("/events/{field_id}", response_model=IrrigationEventResponse)
async def log_irrigation_event(
    field_id: uuid.UUID,
    payload: IrrigationEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Log an applied irrigation event and automatically trigger water balance update."""
    service = IrrigationService(db)
    return await service.create_irrigation_event(field_id, current_user, payload)


@router.delete("/events/{field_id}/{event_id}")
async def delete_irrigation_event(
    field_id: uuid.UUID,
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a logged irrigation event."""
    service = IrrigationService(db)
    await service.delete_irrigation_event(field_id, event_id, current_user)
    return {"ok": True, "message": "Irrigation event deleted."}
