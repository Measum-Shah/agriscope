"""Abstract base interface and common schemas for weather data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass
class DailyWeatherRecord:
    """Standardized daily meteorological record across providers."""

    date: str  # YYYY-MM-DD
    temperature: float  # Mean air temperature at 2m (°C)
    humidity: float  # Relative humidity at 2m (%)
    wind_speed: float  # Wind speed at 2m (m/s)
    solar_radiation: float  # Solar radiation (MJ/m²/day)
    tmin: Optional[float] = None  # Minimum daily temp (°C)
    tmax: Optional[float] = None  # Maximum daily temp (°C)
    precipitation_mm: Optional[float] = None  # Precipitation (mm/day)
    et0_provider: Optional[float] = None  # Provider-calculated ET0 (e.g. Open-Meteo FAO-56 PM)
    provider_name: str = "unknown"
    is_fallback: bool = False
    is_cached: bool = False


@dataclass
class ReverseGeocodeResult:
    """Reverse geocoding / search place match."""

    name: str
    country: str
    latitude: float
    longitude: float
    admin1: Optional[str] = None
    elevation: Optional[float] = None


class WeatherProvider(ABC):
    """Abstract contract for historical, forecast, and geocoding services."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this provider."""
        pass

    @abstractmethod
    async def get_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
    ) -> List[DailyWeatherRecord]:
        """Fetch historical daily meteorological time series."""
        pass

    @abstractmethod
    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
    ) -> List[DailyWeatherRecord]:
        """Fetch 7-day or N-day daily weather forecast."""
        pass

    @abstractmethod
    async def get_daily_inputs(
        self,
        latitude: float,
        longitude: float,
        target_date: date,
    ) -> DailyWeatherRecord:
        """Fetch the four core ML model inputs for a specific point and date."""
        pass
