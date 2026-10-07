"""NASA POWER weather provider wrapping agriscope_ml NASA POWER client with fallback."""

from __future__ import annotations

from datetime import date
from typing import List, Optional

import httpx

from app.core.logging import logger
from app.providers.weather.base import DailyWeatherRecord, WeatherProvider

NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


class NasaPowerProvider(WeatherProvider):
    """Historical daily agroclimatology provider backed by NASA POWER API."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    @property
    def provider_id(self) -> str:
        return "nasa_power"

    async def get_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
    ) -> List[DailyWeatherRecord]:
        params = {
            "parameters": "T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR",
            "community": "AG",
            "longitude": longitude,
            "latitude": latitude,
            "start": start_date.strftime("%Y%m%d"),
            "end": end_date.strftime("%Y%m%d"),
            "format": "JSON",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.get(NASA_POWER_BASE_URL, params=params)
            res.raise_for_status()
            data = res.json()

        properties = data.get("properties", {})
        parameter_dict = properties.get("parameter", {})
        t2m = parameter_dict.get("T2M", {})
        tmax = parameter_dict.get("T2M_MAX", {})
        tmin = parameter_dict.get("T2M_MIN", {})
        rh = parameter_dict.get("RH2M", {})
        ws = parameter_dict.get("WS2M", {})
        solar = parameter_dict.get("ALLSKY_SFC_SW_DWN", {})
        precip = parameter_dict.get("PRECTOTCORR", {})

        records: List[DailyWeatherRecord] = []
        for date_key in sorted(t2m.keys()):
            val_t = t2m.get(date_key)
            if val_t is None or val_t <= -90.0:
                continue

            dt_formatted = f"{date_key[:4]}-{date_key[4:6]}-{date_key[6:]}"
            records.append(
                DailyWeatherRecord(
                    date=dt_formatted,
                    temperature=round(float(val_t), 2),
                    humidity=round(float(rh.get(date_key, 50.0)), 1),
                    wind_speed=round(float(ws.get(date_key, 2.0)), 2),
                    solar_radiation=round(float(solar.get(date_key, 20.0)), 2),
                    tmin=round(float(tmin[date_key]), 2) if date_key in tmin and tmin[date_key] > -90 else None,
                    tmax=round(float(tmax[date_key]), 2) if date_key in tmax and tmax[date_key] > -90 else None,
                    precipitation_mm=round(float(precip[date_key]), 2) if date_key in precip and precip[date_key] >= 0 else 0.0,
                    provider_name=self.provider_id,
                    is_fallback=False,
                    is_cached=False,
                )
            )
        return records

    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
    ) -> List[DailyWeatherRecord]:
        """NASA POWER only provides historical observations. Raises NotImplementedError."""
        raise NotImplementedError("NASA POWER does not provide meteorological forecasts.")

    async def get_daily_inputs(
        self,
        latitude: float,
        longitude: float,
        target_date: date,
    ) -> DailyWeatherRecord:
        records = await self.get_historical(latitude, longitude, target_date, target_date)
        if records:
            return records[0]
        raise ValueError(f"NASA POWER returned no observations for date {target_date}")
