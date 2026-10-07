"""Unit tests for model registry database synchronization and Redis caching."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.ml_model import DataProvenance, MLModel, ModelStatus
from app.services.model_registry_sync import (
    ACTIVE_MODEL_CACHE_KEY,
    get_active_model_cached,
    set_active_model,
    sync_models_to_database,
)


@pytest.mark.asyncio
async def test_sync_models_to_database_idempotent(tmp_path):
    """Verify scanning artifact directory syncs model cards to ml_models table."""
    # Create mock artifact bundle
    bundle_dir = tmp_path / "agriscope_ensemble_basic" / "v1.0"
    bundle_dir.mkdir(parents=True)
    card_data = {
        "model_id": "agriscope_ensemble_basic",
        "algorithm": "ensemble",
        "version": "v1.0",
        "feature_schema": "basic",
        "feature_names": ["temperature", "humidity", "wind_speed", "solar_radiation"],
        "is_synthetic": True,
        "provenance": "synthetic",
        "metrics": {"r2": 0.991},
    }
    with open(bundle_dir / "model_card.json", "w", encoding="utf-8") as f:
        json.dump(card_data, f)

    session = AsyncMock()
    session.add = MagicMock()
    # First call: existing is None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    synced = await sync_models_to_database(session, artifacts_dir=tmp_path)
    assert len(synced) == 1
    model = synced[0]
    assert model.name == "agriscope_ensemble_basic"
    assert model.version == "v1.0"
    assert model.data_provenance == DataProvenance.SYNTHETIC.value
    assert model.status == ModelStatus.ACTIVE.value
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_active_model_cached_redis_hit_and_miss():
    """Verify Redis caching logic: cache hit bypasses DB, cache miss queries DB and sets cache."""
    session = AsyncMock()
    redis = AsyncMock()

    # 1. Test cache HIT
    cached_payload = {
        "id": "model-123",
        "name": "agriscope_ensemble_basic",
        "version": "v1.0",
        "data_provenance": "synthetic",
        "algorithm": "ensemble",
        "feature_schema": {"schema": "basic"},
        "metrics": {},
        "artifact_uri": "artifacts/ensemble",
    }
    redis.get.return_value = json.dumps(cached_payload)

    result_hit = await get_active_model_cached(session, redis_client=redis)
    assert result_hit["name"] == "agriscope_ensemble_basic"
    # Session execute should not be called on cache hit
    session.execute.assert_not_called()

    # 2. Test cache MISS
    redis.get.return_value = None
    db_model = MLModel(
        name="agriscope_svr_basic",
        algorithm="svr",
        version="v1.0",
        data_provenance="synthetic",
        status="active",
        feature_schema={"schema": "basic", "features": []},
        metrics_json={"r2": 0.99},
        artifact_uri="artifacts/svr",
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = db_model
    session.execute.return_value = mock_res

    result_miss = await get_active_model_cached(session, redis_client=redis)
    assert result_miss["name"] == "agriscope_svr_basic"
    # Verify setex called to write cache
    redis.setex.assert_called_once()
    assert redis.setex.call_args[0][0] == ACTIVE_MODEL_CACHE_KEY


@pytest.mark.asyncio
async def test_set_active_model_invalidates_cache():
    """Verify promoting a model updates status and deletes Redis cache key."""
    session = AsyncMock()
    redis = AsyncMock()

    target_model = MLModel(
        name="agriscope_lightgbm_basic",
        version="v1.0",
        algorithm="lightgbm",
        status="pending_approval",
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = target_model
    session.execute.return_value = mock_res

    promoted = await set_active_model(
        session, "agriscope_lightgbm_basic", "v1.0", redis_client=redis
    )
    assert promoted is not None
    assert promoted.status == ModelStatus.ACTIVE.value
    session.commit.assert_called_once()
    redis.delete.assert_called_once_with(ACTIVE_MODEL_CACHE_KEY)
