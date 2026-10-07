"""Field management REST API router."""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, status
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.field_analysis import FieldCreateRequest, FieldResponse, FieldUpdateRequest
from app.services.field_service import FieldService

router = APIRouter(prefix="/fields", tags=["fields"])


def serialize_field(field_obj) -> FieldResponse:
    shapely_geom = to_shape(field_obj.geometry)
    return FieldResponse(
        id=field_obj.id,
        user_id=field_obj.user_id,
        name=field_obj.name,
        crop_id=field_obj.crop_id,
        planting_date=field_obj.planting_date,
        area_ha=field_obj.area_ha,
        geometry=mapping(shapely_geom),
    )


@router.get("", response_model=List[FieldResponse])
async def list_fields(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all fields owned by the authenticated user."""
    service = FieldService(db)
    fields = await service.list_fields(current_user)
    return [serialize_field(f) for f in fields]


@router.post("", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
async def create_field(
    payload: FieldCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new field boundary with PostGIS geometry and entitlement validation."""
    service = FieldService(db)
    field_obj = await service.create_field(
        user=current_user,
        name=payload.name,
        geometry=payload.geometry,
        crop_id=payload.crop_id,
        planting_date=payload.planting_date,
    )
    return serialize_field(field_obj)


@router.get("/{field_id}", response_model=FieldResponse)
async def get_field(
    field_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single field by ID."""
    service = FieldService(db)
    field_obj = await service.get_field(current_user, field_id)
    return serialize_field(field_obj)


@router.patch("/{field_id}", response_model=FieldResponse)
async def update_field(
    field_id: uuid.UUID,
    payload: FieldUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update field metadata or boundary geometry."""
    service = FieldService(db)
    field_obj = await service.update_field(
        user=current_user,
        field_id=field_id,
        name=payload.name,
        crop_id=payload.crop_id,
        planting_date=payload.planting_date,
        geometry=payload.geometry,
    )
    return serialize_field(field_obj)


@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field(
    field_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a field and associated observations."""
    service = FieldService(db)
    await service.delete_field(current_user, field_id)
    return None
