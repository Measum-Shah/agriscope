"""Pydantic schemas for ML inference, batch estimation, and explainability."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def classify_et(et_value: float) -> str:
    """Classify ET value according to AgriScope standards:

    Low: < 2 mm/day
    Moderate: 2 - 5 mm/day
    High: > 5 mm/day
    """
    if et_value < 2.0:
        return "low"
    if et_value <= 5.0:
        return "moderate"
    return "high"


class MeteorologicalInput(BaseModel):
    """Meteorological observations validated against AgriScope physical boundaries."""

    temperature: float = Field(
        ...,
        ge=-10.0,
        le=50.0,
        description="Mean daily temperature in °C [-10, 50]",
    )
    humidity: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Relative humidity in % [0, 100]",
    )
    wind_speed: float = Field(
        ...,
        ge=0.0,
        le=30.0,
        description="Wind speed at 2m in m/s [0, 30]",
    )
    solar_radiation: float = Field(
        ...,
        ge=0.0,
        le=35.0,
        description="Solar radiation in MJ/m²/day [0, 35]",
    )
    tmin: Optional[float] = Field(
        None, ge=-15.0, le=45.0, description="Minimum daily temperature in °C"
    )
    tmax: Optional[float] = Field(
        None, ge=-5.0, le=55.0, description="Maximum daily temperature in °C"
    )
    latitude: Optional[float] = Field(
        None, ge=-90.0, le=90.0, description="Latitude in decimal degrees"
    )
    elevation: Optional[float] = Field(
        None, ge=-400.0, le=5000.0, description="Elevation in meters"
    )
    doy: Optional[int] = Field(None, ge=1, le=366, description="Day of year [1, 366]")


class BatchInferenceRequest(BaseModel):
    """Batch prediction request containing multiple observations."""

    observations: List[MeteorologicalInput] = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Array of meteorological observations (≤ 10,000)",
    )
    model_id: Optional[str] = Field(None, description="Optional target model identifier")
    version: Optional[str] = Field(None, description="Optional target model version")


class InferenceResponse(BaseModel):
    """Prediction outcome with conformal confidence intervals and data provenance."""

    et_value: float = Field(
        ..., description="Estimated reference evapotranspiration (ET0) in mm/day"
    )
    interval_low: float = Field(..., description="Conformal lower bound (90% confidence)")
    interval_high: float = Field(..., description="Conformal upper bound (90% confidence)")
    confidence_level: float = Field(0.90, description="Nominal confidence level")
    classification: str = Field(..., description="Classification category: low, moderate, or high")
    model_id: str
    model_version: str
    data_provenance: str
    is_synthetic: bool
    latency_ms: float


class BatchInferenceResponse(BaseModel):
    """Batch prediction response containing results for all submitted observations."""

    predictions: List[InferenceResponse]
    count: int
    total_latency_ms: float


class ExplainRequest(BaseModel):
    """Request for SHAP feature attribution explanation."""

    observation: MeteorologicalInput
    model_id: Optional[str] = None
    version: Optional[str] = None


class ExplainResponse(BaseModel):
    """SHAP explanation response with additive feature attributions."""

    prediction: float
    base_value: float
    contributions: Dict[str, float]
    feature_ranking: List[str]
    model_id: str
    model_version: str
    latency_ms: float


class LoadModelRequest(BaseModel):
    """Request to hot-swap or load an active model bundle."""

    model_id: str
    version: str


class LoadModelResponse(BaseModel):
    """Confirmation of model hot-swap."""

    success: bool
    message: str
    active_model_id: str
    active_model_version: str


class ModelSummaryResponse(BaseModel):
    """Summary of registered or loaded ML model."""

    model_id: str
    version: str
    algorithm: str
    is_active: bool
    data_provenance: str
    is_synthetic: bool
    metrics: Dict[str, Any]


class MLHealthResponse(BaseModel):
    """Health check response for ML microservice."""

    status: str
    service: str
    version: str
    active_model_id: str
    active_model_version: str
    uptime_seconds: float
    loaded_models: List[str]
