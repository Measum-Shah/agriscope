"""Integration tests for weather API endpoints and graceful degradation."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.user import User, UserRole, UserStatus


async def create_test_user(client: AsyncClient, email: str = "weather_user@agriscope.local") -> str:
    test_engine = client._transport.app.state.test_engine
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    user = User(
        name="Weather Tester",
        email=email,
        password_hash="hashed_pw",
        role=UserRole.FREE.value,
        plan="free",
        status=UserStatus.ACTIVE.value,
        email_verified=True,
    )
    async with factory() as s:
        s.add(user)
        await s.commit()
        await s.refresh(user)

    return create_access_token(data={"sub": str(user.id), "role": user.role, "plan": user.plan})


@pytest.mark.asyncio
async def test_weather_prefill_graceful_degradation(client: AsyncClient):
    """Verify GET /api/v1/weather/prefill falls back to mock provider gracefully when remote APIs fail."""
    token = await create_test_user(client, "degrade_prefill@agriscope.local")

    # Simulate network failure on remote providers
    with patch(
        "app.providers.weather.open_meteo.OpenMeteoProvider.get_daily_inputs",
        side_effect=Exception("Open-Meteo timeout"),
    ), patch(
        "app.providers.weather.nasa_power.NasaPowerProvider.get_daily_inputs",
        side_effect=Exception("NASA POWER connection error"),
    ):
        res = await client.get(
            "/api/v1/weather/prefill",
            params={"latitude": 31.5204, "longitude": 74.3587, "target_date": "2026-06-15"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["provider_name"] == "mock"
        assert data["is_fallback"] is True
        assert -10 <= data["temperature"] <= 50
        assert 0 <= data["humidity"] <= 100
        assert 0 <= data["wind_speed"] <= 30
        assert 0 <= data["solar_radiation"] <= 35


@pytest.mark.asyncio
async def test_weather_forecast_with_ml_cross_check(client: AsyncClient):
    """Verify GET /api/v1/weather/forecast returns 7 days with ML inference and provider ET0."""
    token = await create_test_user(client, "forecast_user@agriscope.local")

    mock_ml_client = AsyncMock()
    mock_ml_client.predict.return_value = AsyncMock(
        et_value=4.62, interval_low=4.12, interval_high=5.12
    )

    with patch("app.services.weather_service.MLClient", return_value=mock_ml_client):
        res = await client.get(
            "/api/v1/weather/forecast",
            params={"latitude": 30.1575, "longitude": 71.5249, "days": 7},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["days"] == 7
        assert len(data["forecast"]) == 7
        for day in data["forecast"]:
            assert "et0_ml" in day
            assert "interval_low" in day
            assert "interval_high" in day
            assert -10 <= day["temperature"] <= 50


@pytest.mark.asyncio
async def test_weather_geocode_endpoint(client: AsyncClient):
    """Verify GET /api/v1/weather/geocode returns location search results."""
    token = await create_test_user(client, "geocode_user@agriscope.local")

    res = await client.get(
        "/api/v1/weather/geocode",
        params={"query": "Lahore"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "latitude" in data[0]
    assert "longitude" in data[0]
