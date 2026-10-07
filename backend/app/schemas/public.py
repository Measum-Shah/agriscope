"""Stable public API schemas for external researcher integrations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PublicPredictRequest(BaseModel):
    temperature: float = Field(..., ge=-10.0, le=50.0, description="Air temperature in degrees Celsius")
    humidity: float = Field(..., ge=0.0, le=100.0, description="Relative humidity in percentage (0-100)")
    wind_speed: float = Field(..., ge=0.0, le=30.0, description="Wind speed at 2m height in m/s")
    solar_radiation: float = Field(..., ge=0.0, le=35.0, description="Solar irradiance in MJ/m²/day")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    elevation_m: Optional[float] = Field(None, ge=-500.0, le=9000.0, description="Elevation above sea level in meters")
    day_of_year: Optional[int] = Field(None, ge=1, le=366, description="Julian day of year (1-366)")


class PublicPredictResponse(BaseModel):
    et_value: float = Field(..., description="Estimated reference evapotranspiration ET₀")
    interval_low: float = Field(..., description="Lower 90% conformal prediction bound")
    interval_high: float = Field(..., description="Upper 90% conformal prediction bound")
    classification: str = Field(..., description="Evaporative demand category (low, moderate, high)")
    fao56_reference: Optional[float] = Field(None, description="FAO-56 Penman-Monteith calculated baseline")
    unit: str = Field("mm/day", description="Unit of evapotranspiration rate")
    model_version: str = Field(..., description="ML model architecture / version tag")
    timestamp: datetime = Field(..., description="UTC timestamp of the estimation event")


class PublicBatchSubmitRequest(BaseModel):
    rows: List[PublicPredictRequest] = Field(
        ..., min_length=1, max_length=1000, description="Array of meteorological input records (max 1000)"
    )


class PublicBatchSubmitResponse(BaseModel):
    job_id: str
    status: str
    total_rows: int


class PublicBatchStatusResponse(BaseModel):
    job_id: str
    status: str
    total_rows: int
    processed_rows: int
    failed_count: int
    download_url: Optional[str] = None


class PublicWeatherPrefillResponse(BaseModel):
    temperature: float
    humidity: float
    wind_speed: float
    solar_radiation: float
    provider: str
    is_fallback: bool = False


class PublicFieldObservationItem(BaseModel):
    date: str
    ndvi: Optional[float] = None
    kc: Optional[float] = None
    et0: Optional[float] = None
    etc: Optional[float] = None


class PublicFieldEtSeriesResponse(BaseModel):
    field_id: str
    field_name: str
    crop_name: Optional[str] = None
    area_ha: float
    observations: List[PublicFieldObservationItem]
