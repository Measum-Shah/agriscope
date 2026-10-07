"""Unit tests for MLClient, retry policy, and circuit breaker."""

from __future__ import annotations

import httpx
import pytest

from app.services.ml_client import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    MLClient,
    MLInferenceError,
    MLServiceTimeoutError,
    MLServiceUnavailableError,
)


def test_circuit_breaker_transitions():
    """Verify circuit breaker state machine: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1, half_open_success_threshold=2)

    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # Record 2 failures (below threshold)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # 3rd failure trips circuit to OPEN
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    # Simulate waiting past recovery timeout
    cb.last_state_change -= 0.2
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # In HALF_OPEN, trial 1 succeeds
    cb.record_success()
    assert cb.state == CircuitState.HALF_OPEN

    # Trial 2 succeeds -> recovered to CLOSED
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_half_open_failure_reopen():
    """Verify trial failure in HALF_OPEN trips circuit back to OPEN immediately."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    # Wait past timeout
    cb.last_state_change -= 0.2
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Trial failure
    cb.record_failure()
    assert cb.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_ml_client_successful_predict_and_explain():
    """Verify MLClient correctly parses responses from a mock server transport."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/infer":
            return httpx.Response(
                200,
                json={
                    "et_value": 4.12,
                    "interval_low": 3.52,
                    "interval_high": 4.72,
                    "confidence_level": 0.90,
                    "classification": "moderate",
                    "model_id": "agriscope_ensemble_basic",
                    "model_version": "v1.0",
                    "data_provenance": "synthetic",
                    "is_synthetic": True,
                    "latency_ms": 12.5,
                },
            )
        if request.url.path == "/explain":
            return httpx.Response(
                200,
                json={
                    "prediction": 4.12,
                    "base_value": 3.80,
                    "contributions": {
                        "temperature": 0.22,
                        "humidity": -0.10,
                        "wind_speed": 0.05,
                        "solar_radiation": 0.15,
                    },
                    "feature_ranking": ["temperature", "solar_radiation", "humidity", "wind_speed"],
                    "model_id": "agriscope_ensemble_basic",
                    "model_version": "v1.0",
                    "latency_ms": 18.2,
                },
            )
        if request.url.path == "/health":
            return httpx.Response(
                200,
                json={
                    "status": "ok",
                    "service": "agriscope-ml-service",
                    "version": "0.1.0",
                    "active_model_id": "agriscope_ensemble_basic",
                    "active_model_version": "v1.0",
                    "uptime_seconds": 120.0,
                    "loaded_models": ["agriscope_ensemble_basic:v1.0"],
                },
            )
        return httpx.Response(404, json={"detail": "Not found"})

    client = MLClient(base_url="http://mock-ml:8001")
    # Patch httpx transport
    mock_transport = httpx.MockTransport(mock_handler)

    async def patched_request(method, path, json_data=None):
        if not client.breaker.can_execute():
            raise CircuitBreakerOpenError("Circuit is OPEN")
        url = f"{client.base_url}{path}"
        async with httpx.AsyncClient(transport=mock_transport) as http:
            resp = await http.request(method, url, json=json_data)
        if resp.status_code >= 400:
            raise MLInferenceError(resp.text)
        client.breaker.record_success()
        return resp.json()

    client._request = patched_request

    # 1. Predict
    obs = {"temperature": 25.0, "humidity": 50.0, "wind_speed": 2.0, "solar_radiation": 18.0}
    pred_res = await client.predict(obs)
    assert pred_res.et_value == 4.12
    assert pred_res.classification == "moderate"
    assert pred_res.is_synthetic is True

    # 2. Explain
    exp_res = await client.explain(obs)
    assert exp_res.prediction == 4.12
    assert "temperature" in exp_res.contributions
    assert exp_res.feature_ranking[0] == "temperature"

    # 3. Health
    h_res = await client.health()
    assert h_res.status == "ok"
    assert h_res.active_model_id == "agriscope_ensemble_basic"


@pytest.mark.asyncio
async def test_ml_client_circuit_breaker_tripping_on_errors():
    """Verify consecutive connection errors trip circuit breaker, fast-failing subsequent calls."""
    client = MLClient(
        base_url="http://unreachable-host:9999",
        timeout=0.1,
        max_retries=0,
        failure_threshold=3,
        recovery_timeout=5.0,
    )

    # 3 failures should trip the breaker
    for _ in range(3):
        with pytest.raises((MLServiceUnavailableError, MLServiceTimeoutError)):
            await client.predict(
                {"temperature": 20.0, "humidity": 50.0, "wind_speed": 2.0, "solar_radiation": 15.0}
            )

    assert client.breaker.state == CircuitState.OPEN

    # 4th call should immediately raise CircuitBreakerOpenError without attempting network
    with pytest.raises(CircuitBreakerOpenError):
        await client.predict(
            {"temperature": 20.0, "humidity": 50.0, "wind_speed": 2.0, "solar_radiation": 15.0}
        )


@pytest.mark.asyncio
async def test_ml_client_no_retry_on_4xx_inference_error():
    """Verify 4xx client errors raise MLInferenceError without useless retries."""

    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "Value out of range"})

    client = MLClient(base_url="http://mock-ml:8001", max_retries=2)
    mock_transport = httpx.MockTransport(error_handler)

    async def patched_request(method, path, json_data=None):
        url = f"{client.base_url}{path}"
        async with httpx.AsyncClient(transport=mock_transport) as http:
            resp = await http.request(method, url, json=json_data)
        if resp.status_code >= 400:
            raise MLInferenceError(resp.text)
        return resp.json()

    client._request = patched_request

    with pytest.raises(MLInferenceError):
        await client.predict(
            {"temperature": 99.0, "humidity": 50.0, "wind_speed": 2.0, "solar_radiation": 15.0}
        )
