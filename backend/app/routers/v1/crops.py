"""Crops reference API router providing FAO-56 crop stage parameters."""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.irrigation import CropResponse
from app.services.irrigation_service import IrrigationService

router = APIRouter(prefix="/crops", tags=["Crops"])


@router.get("", response_model=List[CropResponse])
async def list_crops(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve FAO-56 crop library with growth stages and coefficient values."""
    irrigation_service = IrrigationService(db)
    crops = await irrigation_service.get_crop_library()
    return crops


@router.get("/{crop_id}", response_model=CropResponse)
async def get_crop_detail(
    crop_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve detailed crop parameters and stage duration timeline."""
    irrigation_service = IrrigationService(db)
    crop = await irrigation_service.get_crop_detail(crop_id)
    return crop
