"""Unit tests for weather providers (Mock, Open-Meteo, NASA POWER) with recorded fixtures."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.providers.weather.mock import MockWeatherProvider
from app.providers.weather.nasa_power import NasaPowerProvider
from app.providers.weather.open_meteo import OpenMeteoProvider


@pytest.mark.asyncio
async def test_mock_weather_provider_physics_ranges():
    """Verify mock provider generates meteorologically valid parameter ranges."""
    provider = MockWeatherProvider()
    record = await provider.get_daily_inputs(31.5, 74.3, date(2026, 6, 15))

    assert record.provider_name == "mock"
    assert record.is_fallback is True
    assert -10.0 <= record.temperature <= 50.0
    assert 0.0 <= record.humidity <= 100.0
    assert 0.0 <= record.wind_speed <= 30.0
    assert 0.0 <= record.solar_radiation <= 35.0
    assert record.tmax is not None and record.tmin is not None
    assert record.tmax >= record.tmin
    assert record.et0_provider is not None and record.et0_provider > 0.0


@pytest.mark.asyncio
async def test_open_meteo_provider_with_fixture():
    """Verify Open-Meteo provider parses daily meteorological and FAO-56 fields."""
    provider = OpenMeteoProvider()
    mock_payload = {
        "daily": {
            "time": ["2026-06-15", "2026-06-16"],
            "temperature_2m_mean": [32.4, 33.1],
            "temperature_2m_max": [39.0, 40.2],
            "temperature_2m_min": [26.0, 26.5],
            "relative_humidity_2m_mean": [42.0, 40.0],
            "wind_speed_10m_max": [14.4, 15.0],  # in km/h -> should convert to m/s
            "shortwave_radiation_sum": [24.5, 25.1],
            "precipitation_sum": [0.0, 0.0],
            "et0_fao_evapotranspiration": [5.6, 5.8],
        }
    }

    from unittest.mock import MagicMock

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = mock_payload
        mock_get.return_value = mock_resp

        records = await provider.get_forecast(31.5, 74.3, days=2)
        assert len(records) == 2
        assert records[0].date == "2026-06-15"
        assert records[0].temperature == 32.4
        assert records[0].et0_provider == 5.6
        assert records[0].provider_name == "open_meteo"
        assert records[0].is_fallback is False


@pytest.mark.asyncio
async def test_nasa_power_provider_with_fixture():
    """Verify NASA POWER parser handles daily parameter dictionary."""
    from unittest.mock import MagicMock

    provider = NasaPowerProvider()
    mock_payload = {
        "properties": {
            "parameter": {
                "T2M": {"20260615": 30.5},
                "T2M_MAX": {"20260615": 37.0},
                "T2M_MIN": {"20260615": 24.0},
                "RH2M": {"20260615": 48.0},
                "WS2M": {"20260615": 2.5},
                "ALLSKY_SFC_SW_DWN": {"20260615": 23.2},
                "PRECTOTCORR": {"20260615": 0.0},
            }
        }
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = mock_payload
        mock_get.return_value = mock_resp

        records = await provider.get_historical(31.5, 74.3, date(2026, 6, 15), date(2026, 6, 15))
        assert len(records) == 1
        assert records[0].date == "2026-06-15"
        assert records[0].temperature == 30.5
        assert records[0].wind_speed == 2.5
        assert records[0].solar_radiation == 23.2
        assert records[0].provider_name == "nasa_power"
