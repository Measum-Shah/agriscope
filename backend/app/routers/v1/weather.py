"""Weather endpoints for point prefill, ML-driven 7-day forecast, and historical series."""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.core.plans import redis_client
from app.models.user import User
from app.schemas.weather import (
    ForecastResponse,
    GeocodingResultItem,
    HistoricalSeriesResponse,
    WeatherPrefillResponse,
)
from app.services.weather_service import WeatherService

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/prefill", response_model=WeatherPrefillResponse)
async def get_weather_prefill(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees"),
    target_date: Optional[date] = Query(None, description="Observation date (defaults to today)"),
    current_user: User = Depends(get_current_user),
):
    """Retrieve 4 model inputs (temperature, humidity, wind, solar) for a location and date."""
    dt = target_date or date.today()
    service = WeatherService(redis_client=redis_client)
    res = await service.get_prefill_inputs(latitude=latitude, longitude=longitude, target_date=dt)
    return WeatherPrefillResponse(**res)


@router.get("/forecast", response_model=ForecastResponse)
async def get_weather_forecast(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    days: int = Query(7, ge=1, le=14),
    current_user: User = Depends(get_current_user),
):
    """Retrieve 7-day weather forecast with ML model ET0 inference and provider cross-check."""
    service = WeatherService(redis_client=redis_client)
    res = await service.get_forecast(latitude=latitude, longitude=longitude, days=days)
    return ForecastResponse(**res)


@router.get("/historical", response_model=HistoricalSeriesResponse)
async def get_weather_historical(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    start_date: date = Query(..., description="Start date YYYY-MM-DD"),
    end_date: date = Query(..., description="End date YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
):
    """Retrieve historical daily weather time series with monthly aggregations."""
    service = WeatherService(redis_client=redis_client)
    res = await service.get_historical(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
    )
    return HistoricalSeriesResponse(**res)


@router.get("/geocode", response_model=List[GeocodingResultItem])
async def search_places(
    query: str = Query(..., min_length=2, description="Place or city name to search"),
    limit: int = Query(5, ge=1, le=10),
    current_user: User = Depends(get_current_user),
):
    """Geocode search for city/place lookup."""
    service = WeatherService()
    results = await service.search_places(query=query, limit=limit)
    return [GeocodingResultItem(**r) for r in results]
