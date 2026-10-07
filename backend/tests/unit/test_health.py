"""Tests for API health, readiness, and metrics endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "AgriScope"
    assert "version" in data
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_ready_endpoint(client: AsyncClient):
    response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "redis" in data
    assert "storage" in data
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient):
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "agriscope_http_requests_total" in response.text
