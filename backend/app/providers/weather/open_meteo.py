"""Open-Meteo weather provider for forecasts, ET0 cross-check, and geocoding."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import httpx

from app.core.logging import logger
from app.providers.weather.base import DailyWeatherRecord, ReverseGeocodeResult, WeatherProvider

FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"


class OpenMeteoProvider(WeatherProvider):
    """Fetches high-resolution forecasts including reference ET0 (FAO-56 PM) from Open-Meteo."""

    def __init__(self, timeout: float = 6.0):
        self.timeout = timeout

    @property
    def provider_id(self) -> str:
        return "open_meteo"

    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
    ) -> List[DailyWeatherRecord]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": [
                "temperature_2m_mean",
                "temperature_2m_max",
                "temperature_2m_min",
                "relative_humidity_2m_mean",
                "wind_speed_10m_max",
                "shortwave_radiation_sum",
                "precipitation_sum",
                "et0_fao_evapotranspiration",
            ],
            "timezone": "auto",
            "forecast_days": min(max(days, 1), 16),
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.get(FORECAST_API_URL, params=params)
            res.raise_for_status()
            data = res.json()

        daily = data.get("daily", {})
        times = daily.get("time", [])
        tmean_list = daily.get("temperature_2m_mean", [])
        tmax_list = daily.get("temperature_2m_max", [])
        tmin_list = daily.get("temperature_2m_min", [])
        rh_list = daily.get("relative_humidity_2m_mean", [])
        # Wind at 10m converted to 2m using logarithmic wind profile FAO-56 Eq. 47: u2 = u10 * 4.87 / ln(67.8*10 - 5.42) ~= u10 * 0.748
        wind_10m_list = daily.get("wind_speed_10m_max", [])
        # Solar radiation in MJ/m² (Open-Meteo returns MJ/m² for shortwave_radiation_sum)
        rad_list = daily.get("shortwave_radiation_sum", [])
        precip_list = daily.get("precipitation_sum", [])
        et0_list = daily.get("et0_fao_evapotranspiration", [])

        records: List[DailyWeatherRecord] = []
        for i, dt_str in enumerate(times):
            u10 = wind_10m_list[i] if i < len(wind_10m_list) and wind_10m_list[i] is not None else 3.0
            # Convert km/h to m/s if needed (Open-Meteo default is km/h, but can be m/s)
            u2 = round(float(u10) * 0.75 / 3.6, 2) if float(u10) > 10.0 else round(float(u10) * 0.75, 2)
            solar_mj = round(float(rad_list[i]), 2) if i < len(rad_list) and rad_list[i] is not None else 20.0

            records.append(
                DailyWeatherRecord(
                    date=dt_str,
                    temperature=round(float(tmean_list[i]), 2) if i < len(tmean_list) else 25.0,
                    humidity=round(float(rh_list[i]), 1) if i < len(rh_list) else 50.0,
                    wind_speed=max(0.1, min(30.0, u2)),
                    solar_radiation=max(0.1, min(35.0, solar_mj)),
                    tmin=round(float(tmin_list[i]), 2) if i < len(tmin_list) and tmin_list[i] is not None else None,
                    tmax=round(float(tmax_list[i]), 2) if i < len(tmax_list) and tmax_list[i] is not None else None,
                    precipitation_mm=round(float(precip_list[i]), 2) if i < len(precip_list) and precip_list[i] is not None else 0.0,
                    et0_provider=round(float(et0_list[i]), 2) if i < len(et0_list) and et0_list[i] is not None else None,
                    provider_name=self.provider_id,
                    is_fallback=False,
                    is_cached=False,
                )
            )
        return records

    async def get_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
    ) -> List[DailyWeatherRecord]:
        """Historical data via Open-Meteo archive endpoint if requested."""
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": [
                "temperature_2m_mean",
                "temperature_2m_max",
                "temperature_2m_min",
                "relative_humidity_2m_mean",
                "wind_speed_10m_max",
                "shortwave_radiation_sum",
                "precipitation_sum",
                "et0_fao_evapotranspiration",
            ],
            "timezone": "auto",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.get(url, params=params)
            res.raise_for_status()
            data = res.json()

        daily = data.get("daily", {})
        times = daily.get("time", [])
        tmean_list = daily.get("temperature_2m_mean", [])
        tmax_list = daily.get("temperature_2m_max", [])
        tmin_list = daily.get("temperature_2m_min", [])
        rh_list = daily.get("relative_humidity_2m_mean", [])
        wind_10m_list = daily.get("wind_speed_10m_max", [])
        rad_list = daily.get("shortwave_radiation_sum", [])
        precip_list = daily.get("precipitation_sum", [])
        et0_list = daily.get("et0_fao_evapotranspiration", [])

        records: List[DailyWeatherRecord] = []
        for i, dt_str in enumerate(times):
            u10 = wind_10m_list[i] if i < len(wind_10m_list) and wind_10m_list[i] is not None else 3.0
            u2 = round(float(u10) * 0.75 / 3.6, 2) if float(u10) > 10.0 else round(float(u10) * 0.75, 2)
            solar_mj = round(float(rad_list[i]), 2) if i < len(rad_list) and rad_list[i] is not None else 20.0

            records.append(
                DailyWeatherRecord(
                    date=dt_str,
                    temperature=round(float(tmean_list[i]), 2) if i < len(tmean_list) else 25.0,
                    humidity=round(float(rh_list[i]), 1) if i < len(rh_list) else 50.0,
                    wind_speed=max(0.1, min(30.0, u2)),
                    solar_radiation=max(0.1, min(35.0, solar_mj)),
                    tmin=round(float(tmin_list[i]), 2) if i < len(tmin_list) and tmin_list[i] is not None else None,
                    tmax=round(float(tmax_list[i]), 2) if i < len(tmax_list) and tmax_list[i] is not None else None,
                    precipitation_mm=round(float(precip_list[i]), 2) if i < len(precip_list) and precip_list[i] is not None else 0.0,
                    et0_provider=round(float(et0_list[i]), 2) if i < len(et0_list) and et0_list[i] is not None else None,
                    provider_name=self.provider_id,
                    is_fallback=False,
                    is_cached=False,
                )
            )
        return records

    async def get_daily_inputs(
        self,
        latitude: float,
        longitude: float,
        target_date: date,
    ) -> DailyWeatherRecord:
        today = date.today()
        # If target_date is today or future, query forecast; otherwise archive
        if target_date >= today:
            records = await self.get_forecast(latitude, longitude, days=(target_date - today).days + 1)
        else:
            records = await self.get_historical(latitude, longitude, start_date=target_date, end_date=target_date)

        for r in records:
            if r.date == target_date.isoformat():
                return r
        if records:
            return records[0]
        raise ValueError(f"No weather data found for date {target_date}")

    async def search_places(self, query: str, limit: int = 5) -> List[ReverseGeocodeResult]:
        """Geocoding search via Open-Meteo Geocoding API."""
        params = {"name": query, "count": limit, "language": "en", "format": "json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.get(GEOCODING_API_URL, params=params)
            res.raise_for_status()
            data = res.json()

        results: List[ReverseGeocodeResult] = []
        for item in data.get("results", []):
            results.append(
                ReverseGeocodeResult(
                    name=item.get("name", "Unknown"),
                    country=item.get("country", ""),
                    latitude=float(item.get("latitude")),
                    longitude=float(item.get("longitude")),
                    admin1=item.get("admin1"),
                    elevation=item.get("elevation"),
                )
            )
        return results
