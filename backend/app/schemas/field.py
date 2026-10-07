"""Pydantic schemas for Field entity."""

import uuid
from datetime import date
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class FieldCreate(BaseModel):
    name: str = Field(..., max_length=150)
    crop_id: Optional[uuid.UUID] = None
    planting_date: Optional[date] = None
    area_ha: float = Field(default=1.0, gt=0)
    geometry: Dict[str, Any] = Field(..., description="GeoJSON Polygon geometry")


class FieldRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    crop_id: Optional[uuid.UUID] = None
    planting_date: Optional[date] = None
    area_ha: float

    model_config = ConfigDict(from_attributes=True)
