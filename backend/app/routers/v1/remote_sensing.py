"""Remote sensing analysis REST API router."""

from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.plans import require_plan_feature
from app.db.session import get_db
from app.models.user import User
from app.schemas.field_analysis import FieldObservationResponse, RemoteSensingAnalysisResponse
from app.services.remote_sensing_service import RemoteSensingService

router = APIRouter(prefix="/remote-sensing", tags=["remote-sensing"])


@router.post(
    "/analyze/{field_id}",
    response_model=RemoteSensingAnalysisResponse,
    dependencies=[Depends(require_plan_feature("remote_sensing_enabled"))],
)
async def analyze_field_vegetation(
    field_id: uuid.UUID,
    start_date: Optional[date] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="End date YYYY-MM-DD"),
    cloud_cover_max: float = Query(30.0, ge=0.0, le=100.0, description="Maximum cloud cover percentage"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger multi-temporal Sentinel-2 analysis over field polygon, deriving NDVI/EVI/NDWI and ETc."""
    service = RemoteSensingService(db)
    res = await service.analyze_field(
        user=current_user,
        field_id=field_id,
        start_date=start_date,
        end_date=end_date,
        cloud_cover_max=cloud_cover_max,
    )
    return RemoteSensingAnalysisResponse(**res)


@router.get(
    "/observations/{field_id}",
    response_model=List[FieldObservationResponse],
    dependencies=[Depends(require_plan_feature("remote_sensing_enabled"))],
)
async def get_field_observations(
    field_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query stored historical satellite observations and canopy coefficients for a field."""
    service = RemoteSensingService(db)
    obs = await service.get_field_observations(current_user, field_id)
    return [FieldObservationResponse.model_validate(o) for o in obs]
