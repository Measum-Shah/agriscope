"""Pydantic schemas for Field and Remote Sensing APIs."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class FieldCreateRequest(BaseModel):
    name: str = Field(..., max_length=150)
    crop_id: Optional[uuid.UUID] = None
    planting_date: Optional[date] = None
    geometry: Dict[str, Any] = Field(..., description="GeoJSON Polygon geometry")


class FieldUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    crop_id: Optional[uuid.UUID] = None
    planting_date: Optional[date] = None
    geometry: Optional[Dict[str, Any]] = None


class FieldResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    crop_id: Optional[uuid.UUID] = None
    planting_date: Optional[date] = None
    area_ha: float
    geometry: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class FieldObservationResponse(BaseModel):
    id: uuid.UUID
    field_id: uuid.UUID
    observation_date: date
    ndvi: Optional[float] = None
    evi: Optional[float] = None
    ndwi: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    et0: Optional[float] = None
    kc: Optional[float] = None
    etc: Optional[float] = None
    rain_mm: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class RemoteSensingAnalysisResponse(BaseModel):
    field_id: str
    field_name: str
    observations_count: int
    provider: str
    is_fallback: bool
    series: List[Dict[str, Any]]
