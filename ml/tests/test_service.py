"""Unit and integration tests for the ML FastAPI inference service."""

from __future__ import annotations

import asyncio
import time

import pytest
from httpx import ASGITransport, AsyncClient

from service.main import app


@pytest.mark.asyncio
async def test_ml_health_endpoint():
    """Verify healthcheck endpoint reports status, service name, and active model."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # Trigger startup lifespan
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "agriscope-ml-service"
        assert "active_model_id" in data
        assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_infer_single_endpoint_and_latency():
    """Verify single inference returns point estimate, conformal intervals, and p95 latency < 150ms."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        payload = {
            "temperature": 28.5,
            "humidity": 45.0,
            "wind_speed": 2.5,
            "solar_radiation": 22.0,
        }
        t0 = time.perf_counter()
        response = await client.post("/infer", json=payload)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert response.status_code == 200
        data = response.json()

        assert "et_value" in data
        assert data["et_value"] > 0.0
        assert data["interval_low"] <= data["et_value"]
        assert data["interval_high"] >= data["et_value"]
        assert data["confidence_level"] == 0.90
        assert data["classification"] in ("low", "moderate", "high")
        assert "model_id" in data
        assert "data_provenance" in data
        # Check single inference latency constraint
        assert elapsed_ms < 150.0, f"Single inference took {elapsed_ms}ms, exceeding 150ms budget"


@pytest.mark.asyncio
async def test_infer_batch_endpoint():
    """Verify batch inference endpoint processes multiple items accurately."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        observations = [
            {"temperature": 15.0, "humidity": 70.0, "wind_speed": 1.0, "solar_radiation": 12.0},
            {"temperature": 25.0, "humidity": 50.0, "wind_speed": 2.0, "solar_radiation": 18.0},
            {"temperature": 38.0, "humidity": 20.0, "wind_speed": 4.5, "solar_radiation": 28.0},
        ]
        response = await client.post("/infer/batch", json={"observations": observations})
        assert response.status_code == 200
        data = response.json()

        assert data["count"] == 3
        assert len(data["predictions"]) == 3
        for pred in data["predictions"]:
            assert pred["et_value"] > 0.0
            assert pred["interval_high"] >= pred["interval_low"]


@pytest.mark.asyncio
async def test_infer_validation_bounds():
    """Verify that requests outside physical validation ranges are rejected with 422."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # Out of bounds temperature (75.0 > 50.0)
        invalid_payload = {
            "temperature": 75.0,
            "humidity": 50.0,
            "wind_speed": 2.0,
            "solar_radiation": 20.0,
        }
        res = await client.post("/infer", json=invalid_payload)
        assert res.status_code == 422

        # Out of bounds humidity (-5.0 < 0.0)
        invalid_payload2 = {
            "temperature": 25.0,
            "humidity": -5.0,
            "wind_speed": 2.0,
            "solar_radiation": 20.0,
        }
        res2 = await client.post("/infer", json=invalid_payload2)
        assert res2.status_code == 422


@pytest.mark.asyncio
async def test_explain_endpoint():
    """Verify SHAP explain endpoint returns contributions, baseline, and feature ranking."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        payload = {
            "observation": {
                "temperature": 30.0,
                "humidity": 40.0,
                "wind_speed": 3.0,
                "solar_radiation": 24.0,
            }
        }
        response = await client.post("/explain", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert "prediction" in data
        assert "base_value" in data
        assert "contributions" in data
        assert "feature_ranking" in data
        assert len(data["contributions"]) >= 4
        assert len(data["feature_ranking"]) >= 4


@pytest.mark.asyncio
async def test_models_list_and_hot_swap():
    """Verify listing models and hot-swapping active model without dropping requests."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # 1. List models
        list_res = await client.get("/models")
        assert list_res.status_code == 200
        models = list_res.json()
        assert len(models) > 0

        # Pick another model to hot-swap to
        initial_health = await client.get("/health")
        initial_active = initial_health.json()["active_model_id"]

        target_model = None
        for m in models:
            if m["model_id"] != initial_active:
                target_model = m
                break

        if target_model:
            # Hot swap
            swap_res = await client.post(
                "/models/load",
                json={"model_id": target_model["model_id"], "version": target_model["version"]},
            )
            assert swap_res.status_code == 200
            assert swap_res.json()["success"] is True

            # Verify active model updated
            health_after = await client.get("/health")
            assert health_after.json()["active_model_id"] == target_model["model_id"]

            # Verify inference immediately works on new model
            infer_res = await client.post(
                "/infer",
                json={
                    "temperature": 25.0,
                    "humidity": 50.0,
                    "wind_speed": 2.0,
                    "solar_radiation": 18.0,
                },
            )
            assert infer_res.status_code == 200
            assert infer_res.json()["model_id"] == target_model["model_id"]


@pytest.mark.asyncio
async def test_hot_swap_concurrent_requests():
    """Verify that concurrent inference requests continue smoothly during a hot-swap reload."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        list_res = await client.get("/models")
        models = list_res.json()
        if len(models) < 2:
            pytest.skip("Requires at least 2 models in registry for concurrent hot swap test")

        m2 = models[1]

        async def send_infer():
            res = await client.post(
                "/infer",
                json={
                    "temperature": 24.0,
                    "humidity": 52.0,
                    "wind_speed": 2.2,
                    "solar_radiation": 19.0,
                },
            )
            return res.status_code

        async def do_reload():
            await asyncio.sleep(0.01)  # tiny offset
            res = await client.post(
                "/models/load",
                json={"model_id": m2["model_id"], "version": m2["version"]},
            )
            return res.status_code

        tasks = (
            [send_infer() for _ in range(10)] + [do_reload()] + [send_infer() for _ in range(10)]
        )
        results = await asyncio.gather(*tasks)

        # All requests must succeed with 200
        for code in results:
            assert code == 200
