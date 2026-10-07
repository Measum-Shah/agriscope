"""Mock deterministic weather provider for offline testing and fast degradation fallback."""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import List, Optional

from app.providers.weather.base import DailyWeatherRecord, ReverseGeocodeResult, WeatherProvider


class MockWeatherProvider(WeatherProvider):
    """Generates synthetic, deterministic, realistic agroclimatology observations."""

    @property
    def provider_id(self) -> str:
        return "mock"

    def _generate_record(self, latitude: float, longitude: float, d: date) -> DailyWeatherRecord:
        """Deterministic physics-consistent synthesis based on day-of-year and coordinates."""
        doy = d.timetuple().tm_yday
        # Seasonal temperature wave
        lat_rad = math.radians(latitude)
        base_temp = 25.0 + 10.0 * math.cos(lat_rad) * math.sin(2 * math.pi * (doy - 105) / 365)
        # Diurnal fluctuation
        tmax = round(base_temp + 5.5, 1)
        tmin = round(base_temp - 4.5, 1)
        tmean = round((tmax + tmin) / 2.0, 1)

        # Humidity anti-correlated with temp
        rh = round(max(20.0, min(95.0, 60.0 - 15.0 * math.sin(2 * math.pi * (doy - 105) / 365))), 1)

        # Wind speed moderate 1.5 - 4.0 m/s
        wind = round(2.0 + 1.2 * math.cos(2 * math.pi * doy / 180), 1)

        # Solar radiation peak around summer solstice
        solar = round(max(10.0, min(30.0, 20.0 + 7.5 * math.cos(lat_rad) * math.sin(2 * math.pi * (doy - 80) / 365))), 1)

        # Approximate mock ET0 via simplified Hargreaves/PM
        et0_approx = round(max(1.0, 0.0023 * (tmean + 17.8) * math.sqrt(max(1.0, tmax - tmin)) * (solar * 0.408)), 2)

        return DailyWeatherRecord(
            date=d.isoformat(),
            temperature=tmean,
            humidity=rh,
            wind_speed=wind,
            solar_radiation=solar,
            tmin=tmin,
            tmax=tmax,
            precipitation_mm=0.0 if rh < 70 else 4.5,
            et0_provider=et0_approx,
            provider_name="mock",
            is_fallback=True,
            is_cached=False,
        )

    async def get_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
    ) -> List[DailyWeatherRecord]:
        curr = start_date
        records: List[DailyWeatherRecord] = []
        while curr <= end_date:
            records.append(self._generate_record(latitude, longitude, curr))
            curr += timedelta(days=1)
        return records

    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
    ) -> List[DailyWeatherRecord]:
        today = date.today()
        records: List[DailyWeatherRecord] = []
        for i in range(days):
            records.append(self._generate_record(latitude, longitude, today + timedelta(days=i)))
        return records

    async def get_daily_inputs(
        self,
        latitude: float,
        longitude: float,
        target_date: date,
    ) -> DailyWeatherRecord:
        return self._generate_record(latitude, longitude, target_date)
