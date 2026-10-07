"""Asynchronous ML service client with retries, exponential backoff, and circuit breaker."""

from __future__ import annotations

import asyncio
import time
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import logger


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class MLClientError(Exception):
    """Base exception for ML client errors."""


class CircuitBreakerOpenError(MLClientError):
    """Raised when the circuit breaker is open and fast-failing calls."""


class MLServiceUnavailableError(MLClientError):
    """Raised when the ML microservice is unreachable."""


class MLServiceTimeoutError(MLClientError):
    """Raised when requests to the ML microservice time out."""


class MLInferenceError(MLClientError):
    """Raised when the ML microservice returns a 4xx/5xx failure."""


class CircuitBreaker:
    """In-memory circuit breaker protecting the backend from cascading ML service failures."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 5.0,
        half_open_success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_success_threshold = half_open_success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = time.time()

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if (time.time() - self.last_state_change) >= self.recovery_timeout:
                logger.info("Circuit breaker transitioning from OPEN to HALF_OPEN trial mode.")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        # HALF_OPEN
        return True

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_success_threshold:
                logger.info("Circuit breaker recovering to CLOSED state.")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker trial failed. Tripping back to OPEN.")
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
        elif self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            logger.error(
                f"ML service failure threshold ({self.failure_threshold}) reached. Tripping circuit to OPEN."
            )
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()


class PredictionResult(BaseModel):
    et_value: float
    interval_low: float
    interval_high: float
    confidence_level: float
    classification: str
    model_id: str
    model_version: str
    data_provenance: str
    is_synthetic: bool
    latency_ms: float


class BatchPredictionResult(BaseModel):
    predictions: List[PredictionResult]
    count: int
    total_latency_ms: float


class ExplanationResult(BaseModel):
    prediction: float
    base_value: float
    contributions: Dict[str, float]
    feature_ranking: List[str]
    model_id: str
    model_version: str
    latency_ms: float


class ModelInfo(BaseModel):
    model_id: str
    version: str
    algorithm: str
    is_active: bool
    data_provenance: str
    is_synthetic: bool
    metrics: Dict[str, Any]


class MLServiceHealth(BaseModel):
    status: str
    service: str
    version: str
    active_model_id: str
    active_model_version: str
    uptime_seconds: float
    loaded_models: List[str]


class MLClient:
    """Async client communicating with the AgriScope ML inference microservice."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 5.0,
        max_retries: int = 2,
        failure_threshold: int = 3,
        recovery_timeout: float = 5.0,
    ):
        self.base_url = (base_url or settings.ML_SERVICE_URL).rstrip("/")
        self.timeout = httpx.Timeout(connect=2.0, read=timeout, write=timeout, pool=timeout)
        self.max_retries = max_retries
        self.breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    async def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute HTTP request through circuit breaker with exponential backoff retries."""
        if not self.breaker.can_execute():
            raise CircuitBreakerOpenError(
                "Circuit breaker is OPEN. ML service is temporarily marked unhealthy."
            )

        url = f"{self.base_url}{path}"
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.request(method, url, json=json_data)

                if resp.status_code >= 500:
                    raise MLServiceUnavailableError(
                        f"ML service error ({resp.status_code}): {resp.text}"
                    )
                if resp.status_code >= 400:
                    raise MLInferenceError(
                        f"ML service client error ({resp.status_code}): {resp.text}"
                    )

                self.breaker.record_success()
                return resp.json()

            except (httpx.ConnectError, httpx.NetworkError) as exc:
                last_error = MLServiceUnavailableError(
                    f"Could not connect to ML service at {url}: {exc}"
                )
            except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
                last_error = MLServiceTimeoutError(f"ML service timed out at {url}: {exc}")
            except MLClientError as exc:
                last_error = exc
                if isinstance(exc, MLInferenceError):
                    # Do not retry 4xx errors
                    break
            except Exception as exc:
                last_error = MLClientError(f"Unexpected error calling ML service: {exc}")

            if attempt < self.max_retries:
                backoff = 0.05 * (2**attempt)
                await asyncio.sleep(backoff)

        self.breaker.record_failure()
        if last_error:
            raise last_error
        raise MLServiceUnavailableError("Failed to communicate with ML service.")

    async def predict(self, observation: Dict[str, Any]) -> PredictionResult:
        """Call POST /infer for single observation estimation."""
        data = await self._request("POST", "/infer", json_data=observation)
        return PredictionResult(**data)

    async def predict_batch(self, observations: List[Dict[str, Any]]) -> BatchPredictionResult:
        """Call POST /infer/batch for multiple observations."""
        payload = {"observations": observations}
        data = await self._request("POST", "/infer/batch", json_data=payload)
        return BatchPredictionResult(**data)

    async def explain(self, observation: Dict[str, Any]) -> ExplanationResult:
        """Call POST /explain for SHAP feature attribution."""
        payload = {"observation": observation}
        data = await self._request("POST", "/explain", json_data=payload)
        return ExplanationResult(**data)

    async def health(self) -> MLServiceHealth:
        """Call GET /health."""
        data = await self._request("GET", "/health")
        return MLServiceHealth(**data)

    async def list_models(self) -> List[ModelInfo]:
        """Call GET /models."""
        data = await self._request("GET", "/models")
        return [ModelInfo(**item) for item in data]

    async def load_model(self, model_id: str, version: str) -> Dict[str, Any]:
        """Call POST /models/load to hot-swap active model."""
        payload = {"model_id": model_id, "version": version}
        return await self._request("POST", "/models/load", json_data=payload)
