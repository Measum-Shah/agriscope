"""Unit tests for PredictionService: validation envelopes, quota limits, FAO-56 PM reference, and persistence."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ForbiddenException
from app.core.plans import QuotaService
from app.models.user import User
from app.schemas.prediction import PredictRequest
from app.services.ml_client import PredictionResult
from app.services.prediction_service import (
    PredictionService,
    compute_fao56_reference,
    generate_irrigation_interpretation,
)


@pytest.fixture(autouse=True)
def reset_quota():
    QuotaService.reset_memory_quota()
    yield
    QuotaService.reset_memory_quota()


def test_irrigation_interpretation_categories():
    """Verify generated agronomic text aligns with ET classification thresholds."""
    inter_low = generate_irrigation_interpretation(1.5, "low", 22.0)
    assert "Low evaporative demand" in inter_low
    assert "waterlogging" in inter_low

    inter_mod = generate_irrigation_interpretation(3.8, "moderate", 28.0)
    assert "Moderate evaporative demand" in inter_mod
    assert "active vegetative" in inter_mod

    inter_high = generate_irrigation_interpretation(6.2, "high", 38.0)
    assert "High evaporative demand" in inter_high
    assert "extreme ambient temperatures" in inter_high


def test_compute_fao56_reference():
    """Verify physical FAO-56 reference computation on meteorological inputs."""
    req = PredictRequest(
        temperature=25.0,
        humidity=50.0,
        wind_speed=2.0,
        solar_radiation=18.0,
    )
    val = compute_fao56_reference(req)
    assert val is not None
    assert 2.0 <= val <= 8.0


@pytest.mark.asyncio
async def test_predict_quota_exhaustion_raises():
    """Verify exceeding daily plan quota raises ForbiddenException."""
    mock_ml = AsyncMock()
    service = PredictionService(ml_client=mock_ml)

    user = User(
        id=uuid.uuid4(),
        email="free@agriscope.local",
        plan="free",  # limit 30
    )
    session = AsyncMock()

    # Exhaust quota in memory
    await QuotaService.increment_predictions_today(str(user.id), 30)

    req = PredictRequest(
        temperature=25.0,
        humidity=50.0,
        wind_speed=2.0,
        solar_radiation=18.0,
    )

    with pytest.raises(ForbiddenException, match="Daily prediction limit reached"):
        await service.predict(session=session, user=user, payload=req)


@pytest.mark.asyncio
async def test_predict_sandbox_does_not_persist():
    """Verify What-If sandbox (persist=False) skips database write and quota decrement."""
    mock_ml = AsyncMock()
    mock_ml.predict.return_value = PredictionResult(
        et_value=4.25,
        interval_low=3.65,
        interval_high=4.85,
        confidence_level=0.90,
        classification="moderate",
        model_id="agriscope_ensemble_basic",
        model_version="v1.0",
        data_provenance="synthetic",
        is_synthetic=True,
        latency_ms=15.0,
    )

    service = PredictionService(ml_client=mock_ml)
    user = User(id=uuid.uuid4(), email="free@agriscope.local", plan="free")
    session = AsyncMock()

    req = PredictRequest(
        temperature=28.0,
        humidity=48.0,
        wind_speed=2.2,
        solar_radiation=20.0,
        persist=False,  # Sandbox mode
    )

    res = await service.predict(session=session, user=user, payload=req)

    assert res.id is None
    assert res.et_value == 4.25
    assert res.classification == "moderate"
    # Verify session.add was NOT called
    session.add.assert_not_called()
    # Verify quota counter is still 0
    used = await QuotaService.get_used_predictions_today(str(user.id))
    assert used == 0
