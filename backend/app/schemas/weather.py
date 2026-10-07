"""Pydantic schemas for weather prefill, forecast, and historical series."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WeatherPrefillResponse(BaseModel):
    """Prefill model inputs for a specific coordinate and date."""

    date: str
    temperature: float = Field(..., ge=-10.0, le=50.0)
    humidity: float = Field(..., ge=0.0, le=100.0)
    wind_speed: float = Field(..., ge=0.0, le=30.0)
    solar_radiation: float = Field(..., ge=0.0, le=35.0)
    tmin: Optional[float] = None
    tmax: Optional[float] = None
    precipitation_mm: Optional[float] = None
    et0_provider: Optional[float] = None
    provider_name: str
    is_fallback: bool
    is_cached: bool


class ForecastDayItem(BaseModel):
    date: str
    temperature: float
    humidity: float
    wind_speed: float
    solar_radiation: float
    precipitation_mm: float
    et0_ml: float
    interval_low: float
    interval_high: float
    et0_provider: Optional[float] = None


class ForecastResponse(BaseModel):
    latitude: float
    longitude: float
    days: int
    provider: str
    is_fallback: bool
    is_cached: bool
    forecast: List[ForecastDayItem]


class MonthlyAggregationItem(BaseModel):
    month: str  # YYYY-MM
    mean_et0: float
    total_days: int


class HistoricalSeriesResponse(BaseModel):
    latitude: float
    longitude: float
    start_date: str
    end_date: str
    provider: str
    is_fallback: bool
    is_cached: bool
    series: List[Dict[str, Any]]
    monthly_summary: List[MonthlyAggregationItem]


class GeocodingResultItem(BaseModel):
    name: str
    country: str
    latitude: float
    longitude: float
    admin1: Optional[str] = None
    elevation: Optional[float] = None
