"""Pydantic schemas for Prediction requests, responses, comparisons, and history."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MeteorologicalBase(BaseModel):
    """Core meteorological inputs with validation ranges."""

    temperature: float = Field(..., ge=-10.0, le=50.0, description="Temperature in °C [-10, 50]")
    humidity: float = Field(..., ge=0.0, le=100.0, description="Relative humidity in % [0, 100]")
    wind_speed: float = Field(..., ge=0.0, le=30.0, description="Wind speed at 2m in m/s [0, 30]")
    solar_radiation: float = Field(
        ..., ge=0.0, le=35.0, description="Solar radiation in MJ/m²/day [0, 35]"
    )

    tmin: Optional[float] = Field(None, ge=-20.0, le=50.0, description="Tmin in °C")
    tmax: Optional[float] = Field(None, ge=-10.0, le=60.0, description="Tmax in °C")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Latitude in degrees")
    elevation: Optional[float] = Field(None, ge=-500.0, le=9000.0, description="Elevation in meters")
    doy: Optional[int] = Field(None, ge=1, le=366, description="Day of year [1, 366]")


class PredictRequest(MeteorologicalBase):
    """Prediction request for single observation estimation."""

    field_id: Optional[uuid.UUID] = None
    source: str = "manual"
    is_saved: bool = False
    tags: List[str] = Field(default_factory=list)
    note: Optional[str] = None
    persist: bool = True  # Set to False in What-If sandbox to prevent database clutter


class PredictResponse(BaseModel):
    """Prediction outcome with conformal confidence intervals, classification, and FAO-56 comparison."""

    id: Optional[uuid.UUID] = None
    et_value: float = Field(..., description="Estimated reference ET0 in mm/day (2 decimals)")
    interval_low: float = Field(..., description="Conformal prediction lower bound (90% confidence)")
    interval_high: float = Field(..., description="Conformal prediction upper bound (90% confidence)")
    confidence_level: float = Field(0.90, description="Nominal confidence level")
    classification: str = Field(..., description="Classification category: low, moderate, or high")
    irrigation_interpretation: str = Field(..., description="Agronomic guidance interpretation")

    model_id: str
    model_version: str
    model_algorithm: str
    data_provenance: str
    is_synthetic: bool

    fao56_reference_value: Optional[float] = Field(
        None, description="Physical FAO-56 Penman-Monteith reference value"
    )
    quota_remaining: int
    timestamp: datetime
    latency_ms: float


class CompareModelItem(BaseModel):
    """Evaluation item for a model in multi-model comparison."""

    algorithm: str
    model_id: str
    version: str
    et_value: float
    interval_low: float
    interval_high: float
    classification: str
    metrics: Dict[str, Any] = Field(default_factory=dict)


class ComparePredictResponse(BaseModel):
    """Side-by-side comparison of active-family models against ensemble and physics."""

    reference_et: float
    fao56_reference: Optional[float] = None
    models: List[CompareModelItem]


class ExplainPredictRequest(MeteorologicalBase):
    """Request for SHAP feature attribution on meteorological observations."""

    model_id: Optional[str] = None
    version: Optional[str] = None


class ExplainPredictResponse(BaseModel):
    """SHAP explanation response."""

    prediction: float
    base_value: float
    contributions: Dict[str, float]
    feature_ranking: List[str]
    model_id: str
    model_version: str


class PredictionCreate(MeteorologicalBase):
    """Internal model for persistence."""

    field_id: Optional[uuid.UUID] = None
    source: str = "manual"
    tags: List[str] = Field(default_factory=list)
    note: Optional[str] = None


class PredictionRead(BaseModel):
    """Full prediction record for history lists and detail views."""

    id: uuid.UUID
    user_id: uuid.UUID
    model_id: Optional[uuid.UUID] = None
    field_id: Optional[uuid.UUID] = None
    source: str
    temperature: float
    humidity: float
    wind_speed: float
    solar_radiation: float
    tmin: Optional[float] = None
    tmax: Optional[float] = None
    latitude: Optional[float] = None
    elevation_m: Optional[float] = None
    day_of_year: Optional[int] = None
    et_value: float
    interval_low: Optional[float] = None
    interval_high: Optional[float] = None
    classification: str
    is_saved: bool
    tags: List[str]
    note: Optional[str] = None
    feature_contributions: Dict[str, Any]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class HistoryUpdate(BaseModel):
    """Partial update payload for history bookmarks, tags, and notes."""

    is_saved: Optional[bool] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None


class BulkDeleteRequest(BaseModel):
    """Request payload for bulk deleting prediction records."""

    ids: List[uuid.UUID] = Field(..., min_length=1, description="List of prediction IDs to delete")


class HistoryListResponse(BaseModel):
    """Server-paginated history response."""

    items: List[PredictionRead]
    total: int
    page: int
    page_size: int
    pages: int
    is_capped: bool = False  # True when Free tier caps history view to 50 items


class HistoryStatsResponse(BaseModel):
    """Dashboard statistics and trend summaries."""

    predictions_today: int
    predictions_total: int
    latest_et: Optional[float] = None
    quota_remaining: int
    recent_activity: List[PredictionRead] = Field(default_factory=list)
    trend_7d: List[Dict[str, Any]] = Field(default_factory=list)
