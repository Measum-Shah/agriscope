"""Pydantic schemas for Crops and Irrigation APIs."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CropStageResponse(BaseModel):
    id: uuid.UUID
    crop_id: uuid.UUID
    stage_name: str
    duration_days: int

    model_config = ConfigDict(from_attributes=True)


class CropResponse(BaseModel):
    id: uuid.UUID
    name: str
    scientific_name: Optional[str] = None
    kc_ini: float
    kc_mid: float
    kc_end: float
    description: Optional[str] = None
    stages: List[CropStageResponse] = []

    model_config = ConfigDict(from_attributes=True)


class IrrigationEventCreate(BaseModel):
    event_date: date
    water_applied_mm: float = Field(..., gt=0, le=300, description="Depth of water applied in mm")
    method: str = Field(default="drip", description="Application method: drip, sprinkler, flood, furrow")
    notes: Optional[str] = Field(default=None, max_length=500)


class IrrigationEventResponse(BaseModel):
    id: uuid.UUID
    field_id: uuid.UUID
    event_date: date
    water_applied_mm: float
    method: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SoilBalanceDay(BaseModel):
    date: date
    et0_mm: float
    kc: float
    etc_mm: float
    rain_mm: float
    effective_rain_mm: float
    irrigation_applied_mm: float
    root_depth_m: float
    taw_mm: float
    raw_mm: float
    depletion_mm: float
    is_stress: bool
    irrigation_recommended_mm: float


class IrrigationScheduleDay(BaseModel):
    date: date
    day_name: str
    depletion_mm: float
    raw_threshold_mm: float
    is_irrigation_due: bool = False
    recommended_depth_mm: float = 0.0
    recommended_volume_m3_per_ha: float = 0.0
    recommended_volume_m3_total: float = 0.0
    reason: str


class SeasonSummary(BaseModel):
    total_etc_mm: float
    total_rainfall_mm: float
    total_effective_rain_mm: float
    total_irrigation_applied_mm: float
    net_irrigation_requirement_mm: float
    current_depletion_mm: float
    raw_mm: float
    taw_mm: float
    status: str  # optimal, caution, stress, saturated


class FieldIrrigationPlanResponse(BaseModel):
    field_id: uuid.UUID
    field_name: str
    crop_name: Optional[str] = None
    area_ha: float
    soil_type: str
    planting_date: Optional[date] = None
    mad_fraction: float
    summary: SeasonSummary
    schedule: List[IrrigationScheduleDay]
    daily_balance: List[SoilBalanceDay]
    events: List[IrrigationEventResponse]
