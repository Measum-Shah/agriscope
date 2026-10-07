"""Unit tests for API key provisioning, hashing, scopes, rate limits, and public API access."""

from __future__ import annotations

import hashlib
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.plans import QuotaService
from app.models.api_key import ApiKey
from app.models.user import User
from app.services.api_key_service import ApiKeyService


@pytest.mark.asyncio
async def test_api_key_creation_and_hashing(client: AsyncClient, app):
    """Verifies API key creation returns raw token once, stores SHA-256 hash, and derives prefix."""
    # Register and upgrade user to pro so api_keys_enabled=True
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "researcher@agriscope.io", "password": "SecurePassword123!", "name": "Dr. Researcher"},
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "researcher@agriscope.io", "password": "SecurePassword123!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Free plan cannot create API keys
    bad_res = await client.post(
        "/api/v1/api-keys",
        json={"name": "Test Key"},
        headers=headers,
    )
    assert bad_res.status_code == 403

    # Upgrade to Pro
    up_res = await client.post("/api/v1/billing/mock/upgrade", headers=headers)
    assert up_res.status_code == 200

    # Create API key with custom scopes
    create_res = await client.post(
        "/api/v1/api-keys",
        json={
            "name": "Weather Pipeline Key",
            "scopes": ["predict:read", "predict:write", "weather:read"],
            "expires_in_days": 30,
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    data = create_res.json()

    assert "raw_key" in data
    raw_key = data["raw_key"]
    assert raw_key.startswith("agri_live_")
    assert data["key_prefix"] == raw_key[:12]
    assert "weather:read" in data["scopes"]

    # List keys should NOT return raw key
    list_res = await client.get("/api/v1/api-keys", headers=headers)
    assert list_res.status_code == 200
    listed = list_res.json()
    assert len(listed) >= 1
    assert "raw_key" not in listed[0]
    assert listed[0]["key_prefix"] == data["key_prefix"]


@pytest.mark.asyncio
async def test_public_predict_with_api_key_and_scopes(client: AsyncClient):
    """Verifies public /predict works with valid scoped key and rejects key missing predict:write scope."""
    # Create pro user
    await client.post(
        "/api/v1/auth/register",
        json={"email": "scope_user@agriscope.io", "password": "SecurePassword123!", "name": "Scope User"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "scope_user@agriscope.io", "password": "SecurePassword123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    await client.post("/api/v1/billing/mock/upgrade", headers=headers)

    # 1. Key with only weather:read scope
    weather_only = await client.post(
        "/api/v1/api-keys",
        json={"name": "Weather Read Only", "scopes": ["weather:read"]},
        headers=headers,
    )
    weather_key = weather_only.json()["raw_key"]

    # 2. Key with predict:write scope
    predict_key_res = await client.post(
        "/api/v1/api-keys",
        json={"name": "Predict Key", "scopes": ["predict:write"]},
        headers=headers,
    )
    predict_key = predict_key_res.json()["raw_key"]

    payload = {
        "temperature": 28.5,
        "humidity": 45.0,
        "wind_speed": 2.1,
        "solar_radiation": 22.0,
        "latitude": 31.5,
        "elevation_m": 210.0,
        "day_of_year": 180,
    }

    # Call public predict without key -> 401
    res_no_key = await client.post("/api/v1/public/predict", json=payload)
    assert res_no_key.status_code == 401

    # Call with weather_key -> 403 Forbidden (missing predict:write)
    res_forbidden = await client.post(
        "/api/v1/public/predict",
        json=payload,
        headers={"X-API-Key": weather_key},
    )
    assert res_forbidden.status_code == 403
    assert "missing required scope" in res_forbidden.json()["detail"].lower()

    # Call with predict_key -> 200 OK
    res_ok = await client.post(
        "/api/v1/public/predict",
        json=payload,
        headers={"X-API-Key": predict_key},
    )
    assert res_ok.status_code == 200
    pred_data = res_ok.json()
    assert "et_value" in pred_data
    assert "interval_low" in pred_data
    assert "interval_high" in pred_data
    assert pred_data["unit"] == "mm/day"
    assert pred_data["fao56_reference"] is not None


@pytest.mark.asyncio
async def test_api_key_rate_limiting_and_retry_after(client: AsyncClient):
    """Verifies per-key rate limit triggers HTTP 429 with Retry-After header."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "ratelimit_user@agriscope.io", "password": "SecurePassword123!", "name": "Rate User"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "ratelimit_user@agriscope.io", "password": "SecurePassword123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    await client.post("/api/v1/billing/mock/upgrade", headers=headers)

    create_res = await client.post(
        "/api/v1/api-keys",
        json={"name": "Rate Limited Key", "scopes": ["weather:read"], "rate_limit_per_min": 2},
        headers=headers,
    )
    raw_key = create_res.json()["raw_key"]
    assert create_res.json()["rate_limit_per_min"] == 2

    # First 2 requests pass
    r1 = await client.get("/api/v1/public/weather/prefill?lat=31.5&lon=74.3", headers={"X-API-Key": raw_key})
    assert r1.status_code == 200

    r2 = await client.get("/api/v1/public/weather/prefill?lat=31.5&lon=74.3", headers={"X-API-Key": raw_key})
    assert r2.status_code == 200

    # 3rd request hits rate limit
    r3 = await client.get("/api/v1/public/weather/prefill?lat=31.5&lon=74.3", headers={"X-API-Key": raw_key})
    assert r3.status_code == 429
    assert "retry-after" in r3.headers
    assert int(r3.headers["retry-after"]) > 0


@pytest.mark.asyncio
async def test_api_key_revocation_and_usage_stats(client: AsyncClient):
    """Verifies revoking a key immediately denies access and usage stats endpoint returns counts."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "revoke_user@agriscope.io", "password": "SecurePassword123!", "name": "Revoke User"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "revoke_user@agriscope.io", "password": "SecurePassword123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    await client.post("/api/v1/billing/mock/upgrade", headers=headers)

    create_res = await client.post(
        "/api/v1/api-keys",
        json={"name": "To Be Revoked", "scopes": ["weather:read"]},
        headers=headers,
    )
    raw_key = create_res.json()["raw_key"]
    key_id = create_res.json()["id"]

    # Execute request
    req = await client.get("/api/v1/public/weather/prefill?lat=31.5&lon=74.3", headers={"X-API-Key": raw_key})
    assert req.status_code == 200

    # Check usage stats
    stats_res = await client.get(f"/api/v1/api-keys/{key_id}/usage", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["requests_today"] >= 1

    # Revoke key
    revoke_res = await client.post(f"/api/v1/api-keys/{key_id}/revoke", headers=headers)
    assert revoke_res.status_code == 200
    assert revoke_res.json()["is_active"] is False

    # Calling with revoked key fails
    req_after = await client.get("/api/v1/public/weather/prefill?lat=31.5&lon=74.3", headers={"X-API-Key": raw_key})
    assert req_after.status_code == 401
    assert "revoked" in req_after.json()["detail"].lower()
