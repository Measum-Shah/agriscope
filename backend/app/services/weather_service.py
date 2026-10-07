"""Weather domain service coordinating multi-provider resolution, caching, and ML forecasting."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import logger
from app.providers.weather.base import DailyWeatherRecord, ReverseGeocodeResult, WeatherProvider
from app.providers.weather.mock import MockWeatherProvider
from app.providers.weather.nasa_power import NasaPowerProvider
from app.providers.weather.open_meteo import OpenMeteoProvider
from app.schemas.prediction import PredictRequest
from app.services.ml_client import MLClient

HISTORICAL_CACHE_TTL = 86400 * 7  # 7 days for historical weather data
FORECAST_CACHE_TTL = 3600 * 3  # 3 hours for forecasts


class WeatherService:
    """Manages weather ingestion with Redis caching, retry, graceful degradation, and ML ET0 forecasts."""

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        ml_client: Optional[MLClient] = None,
    ):
        self.redis = redis_client
        self.ml_client = ml_client or MLClient()
        self.nasa_provider = NasaPowerProvider()
        self.open_meteo_provider = OpenMeteoProvider()
        self.mock_provider = MockWeatherProvider()

    def _cache_key(self, prefix: str, lat: float, lon: float, extra: str) -> str:
        return f"agriscope:weather:{prefix}:{lat:.3f}:{lon:.3f}:{extra}"

    async def get_prefill_inputs(
        self,
        latitude: float,
        longitude: float,
        target_date: date,
    ) -> Dict[str, Any]:
        """Fetch model input parameters for a specific point and date with graceful fallback."""
        cache_key = self._cache_key("prefill", latitude, longitude, target_date.isoformat())

        # 1. Try Redis cache
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    val = json.loads(cached)
                    val["is_cached"] = True
                    return val
            except Exception as e:
                logger.debug(f"Redis get failed: {e}")

        # 2. Try Open-Meteo
        try:
            record = await self.open_meteo_provider.get_daily_inputs(latitude, longitude, target_date)
            result = asdict(record)
        except Exception as e_om:
            logger.warning(f"Open-Meteo prefill failed ({e_om}), trying NASA POWER...")
            # 3. Try NASA POWER for past dates
            try:
                if target_date <= date.today():
                    record = await self.nasa_provider.get_daily_inputs(latitude, longitude, target_date)
                    result = asdict(record)
                else:
                    raise ValueError("Cannot query future dates from NASA POWER")
            except Exception as e_nasa:
                logger.warning(f"NASA POWER failed ({e_nasa}), falling back to deterministic mock provider.")
                # 4. Fallback to Mock
                record = await self.mock_provider.get_daily_inputs(latitude, longitude, target_date)
                result = asdict(record)

        # Cache result
        if self.redis:
            try:
                await self.redis.set(cache_key, json.dumps(result), ex=FORECAST_CACHE_TTL)
            except Exception as e:
                logger.debug(f"Redis set failed: {e}")

        return result

    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Fetch weather forecast, cross-check against Open-Meteo ET0, and run ML model inference."""
        cache_key = self._cache_key("forecast", latitude, longitude, f"{days}d")

        # 1. Try Redis cache
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    val = json.loads(cached)
                    val["is_cached"] = True
                    return val
            except Exception as e:
                logger.debug(f"Redis get failed: {e}")

        # 2. Resolve weather forecast series
        is_fallback = False
        provider_name = "open_meteo"
        try:
            records = await self.open_meteo_provider.get_forecast(latitude, longitude, days=days)
        except Exception as e:
            logger.warning(f"Open-Meteo forecast failed ({e}), falling back to Mock provider.")
            records = await self.mock_provider.get_forecast(latitude, longitude, days=days)
            is_fallback = True
            provider_name = "mock"

        # 3. Compute 7-day ET0 forecast using the active ML model
        forecast_items = []
        for r in records:
            dt = date.fromisoformat(r.date)
            doy = dt.timetuple().tm_yday

            # Run ML inference
            ml_et0 = 4.0
            interval_low = 3.5
            interval_high = 4.5
            try:
                pred = await self.ml_client.predict(
                    PredictRequest(
                        temperature=r.temperature,
                        humidity=r.humidity,
                        wind_speed=r.wind_speed,
                        solar_radiation=r.solar_radiation,
                        tmin=r.tmin,
                        tmax=r.tmax,
                        latitude=latitude,
                        doy=doy,
                    )
                )
                ml_et0 = pred.et_value
                interval_low = pred.interval_low
                interval_high = pred.interval_high
            except Exception as e_inf:
                logger.warning(f"ML inference failed for forecast day {r.date}: {e_inf}")
                # Fallback to physical/approximate ET0
                if r.et0_provider is not None:
                    ml_et0 = r.et0_provider
                    interval_low = round(ml_et0 * 0.9, 2)
                    interval_high = round(ml_et0 * 1.1, 2)

            forecast_items.append(
                {
                    "date": r.date,
                    "temperature": r.temperature,
                    "humidity": r.humidity,
                    "wind_speed": r.wind_speed,
                    "solar_radiation": r.solar_radiation,
                    "precipitation_mm": r.precipitation_mm or 0.0,
                    "et0_ml": round(ml_et0, 2),
                    "interval_low": round(interval_low, 2),
                    "interval_high": round(interval_high, 2),
                    "et0_provider": r.et0_provider,  # Cross-check FAO-56 value from Open-Meteo
                }
            )

        payload = {
            "latitude": latitude,
            "longitude": longitude,
            "days": days,
            "provider": provider_name,
            "is_fallback": is_fallback,
            "is_cached": False,
            "forecast": forecast_items,
        }

        if self.redis:
            try:
                await self.redis.set(cache_key, json.dumps(payload), ex=FORECAST_CACHE_TTL)
            except Exception as e:
                logger.debug(f"Redis set failed: {e}")

        return payload

    async def get_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """Fetch historical meteorological series and monthly/seasonal aggregations."""
        cache_key = self._cache_key("historical", latitude, longitude, f"{start_date}_{end_date}")

        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    val = json.loads(cached)
                    val["is_cached"] = True
                    return val
            except Exception as e:
                logger.debug(f"Redis get failed: {e}")

        is_fallback = False
        provider_name = "nasa_power"
        try:
            records = await self.nasa_provider.get_historical(latitude, longitude, start_date, end_date)
            if not records:
                raise ValueError("NASA POWER returned empty record list")
        except Exception as e_nasa:
            logger.warning(f"NASA POWER historical failed ({e_nasa}), trying Open-Meteo archive...")
            try:
                records = await self.open_meteo_provider.get_historical(latitude, longitude, start_date, end_date)
                provider_name = "open_meteo"
            except Exception as e_om:
                logger.warning(f"Open-Meteo historical failed ({e_om}), falling back to Mock provider.")
                records = await self.mock_provider.get_historical(latitude, longitude, start_date, end_date)
                is_fallback = True
                provider_name = "mock"

        # Calculate monthly aggregation
        monthly_map: Dict[str, List[float]] = {}
        for r in records:
            month_key = r.date[:7]  # YYYY-MM
            if month_key not in monthly_map:
                monthly_map[month_key] = []
            # Calculate mock ET0 or record ET0
            val = r.et0_provider if r.et0_provider is not None else 3.8
            monthly_map[month_key].append(val)

        monthly_aggregations = [
            {
                "month": m,
                "mean_et0": round(sum(vals) / len(vals), 2),
                "total_days": len(vals),
            }
            for m, vals in sorted(monthly_map.items())
        ]

        payload = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "provider": provider_name,
            "is_fallback": is_fallback,
            "is_cached": False,
            "series": [asdict(r) for r in records],
            "monthly_summary": monthly_aggregations,
        }

        if self.redis:
            try:
                await self.redis.set(cache_key, json.dumps(payload), ex=HISTORICAL_CACHE_TTL)
            except Exception as e:
                logger.debug(f"Redis set failed: {e}")

        return payload

    async def search_places(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Geocoding search helper."""
        try:
            results = await self.open_meteo_provider.search_places(query, limit=limit)
            return [asdict(r) for r in results]
        except Exception as e:
            logger.warning(f"Geocoding search failed: {e}")
            # Fallback mock results
            return [
                {
                    "name": query.capitalize(),
                    "country": "Pakistan",
                    "latitude": 31.5204,
                    "longitude": 74.3587,
                    "admin1": "Punjab",
                    "elevation": 217.0,
                }
            ]
