"""Synchronization of ML artifact store with PostgreSQL ml_models table and Redis caching."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.ml_model import DataProvenance, MLModel, ModelStatus

try:
    import redis.asyncio as aioredis

    default_redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    default_redis_client = None

ACTIVE_MODEL_CACHE_KEY = "agriscope:active_model_metadata"
CACHE_TTL_SECONDS = 300


def find_artifacts_directory() -> Path:
    """Resolve artifacts directory relative to backend or ml package."""
    candidates = [
        Path("ml/artifacts"),
        Path("../ml/artifacts"),
        Path("../../ml/artifacts"),
        Path("artifacts"),
    ]
    for cand in candidates:
        if cand.exists() and cand.is_dir():
            return cand
    return Path("ml/artifacts")


async def sync_models_to_database(
    session: AsyncSession,
    artifacts_dir: Optional[str | Path] = None,
) -> List[MLModel]:
    """Scan artifact bundles in filesystem/MinIO and sync them to ml_models table."""
    base_dir = Path(artifacts_dir) if artifacts_dir else find_artifacts_directory()
    synced_models: List[MLModel] = []

    if not base_dir.exists():
        logger.warning(f"Artifacts directory '{base_dir}' does not exist. Skipping DB sync.")
        return synced_models

    logger.info(f"Scanning artifact store at: {base_dir}")

    # Discover model_card.json files
    card_files = list(base_dir.rglob("model_card.json"))
    for card_file in card_files:
        try:
            with open(card_file, "r", encoding="utf-8") as f:
                card_data = json.load(f)

            model_id = card_data.get("model_id", card_file.parent.parent.name)
            version = card_data.get("version", card_file.parent.name)
            algorithm = card_data.get("algorithm", "unknown")
            is_synthetic = card_data.get("is_synthetic", False)
            provenance = (
                DataProvenance.SYNTHETIC.value
                if is_synthetic or card_data.get("provenance") == "synthetic"
                else DataProvenance.REAL_DERIVED.value
            )

            # Check if model already exists
            stmt = select(MLModel).where(MLModel.version == version, MLModel.name == model_id)
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()

            # Determine status: active if ensemble bootstrap v1.0, else pending_approval
            is_default_active = (model_id == "agriscope_ensemble_basic" and version == "v1.0") or (
                len(synced_models) == 0 and not existing
            )

            target_status = (
                ModelStatus.ACTIVE.value
                if is_default_active
                else (existing.status if existing else ModelStatus.PENDING_APPROVAL.value)
            )

            if existing is None:
                new_model = MLModel(
                    name=model_id,
                    algorithm=algorithm,
                    version=version,
                    feature_schema={
                        "schema": card_data.get("feature_schema", "basic"),
                        "features": card_data.get("feature_names", []),
                    },
                    metrics_json=card_data.get("metrics", {}),
                    artifact_uri=str(card_file.parent),
                    status=target_status,
                    data_provenance=provenance,
                    trained_by="system",
                )
                session.add(new_model)
                synced_models.append(new_model)
                logger.info(
                    f"Registered new ML model in DB: {model_id}:{version} (status={target_status})"
                )
            else:
                existing.metrics_json = card_data.get("metrics", {})
                existing.data_provenance = provenance
                existing.artifact_uri = str(card_file.parent)
                synced_models.append(existing)

        except Exception as e:
            logger.error(f"Failed to parse model card at {card_file}: {e}")

    await session.commit()
    return synced_models


async def get_active_model_cached(
    session: AsyncSession,
    redis_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Retrieve active model metadata with Redis caching and PostgreSQL fallback."""
    r = redis_client or default_redis_client

    # 1. Try Redis cache
    if r is not None:
        try:
            cached_val = await r.get(ACTIVE_MODEL_CACHE_KEY)
            if cached_val:
                return json.loads(cached_val)
        except Exception as e:
            logger.warning(f"Redis get failed for active model metadata: {e}")

    # 2. Query DB
    try:
        stmt = (
            select(MLModel)
            .where(MLModel.status == ModelStatus.ACTIVE.value)
            .order_by(MLModel.created_at.desc())
        )
        result = await session.execute(stmt)
        active_model = result.scalar_one_or_none()
    except Exception as e:
        logger.warning(f"Failed to query active MLModel: {e}")
        active_model = None

    if isinstance(active_model, MLModel):
        metadata: Dict[str, Any] = {
            "id": str(active_model.id),
            "name": active_model.name,
            "algorithm": active_model.algorithm,
            "version": active_model.version,
            "data_provenance": active_model.data_provenance,
            "feature_schema": active_model.feature_schema,
            "metrics": active_model.metrics_json,
            "artifact_uri": active_model.artifact_uri,
        }
    else:
        # Fallback bootstrap active definition
        metadata = {
            "id": "bootstrap-active",
            "name": "agriscope_ensemble_basic",
            "algorithm": "ensemble",
            "version": "v1.0",
            "data_provenance": DataProvenance.SYNTHETIC.value,
            "feature_schema": {"schema": "basic", "features": []},
            "metrics": {},
            "artifact_uri": "ml/artifacts/agriscope_ensemble_basic/v1.0",
        }

    # 3. Write to Redis cache
    if r is not None:
        try:
            await r.setex(ACTIVE_MODEL_CACHE_KEY, CACHE_TTL_SECONDS, json.dumps(metadata))
        except Exception as e:
            logger.warning(f"Redis setex failed for active model metadata: {e}")

    return metadata


async def set_active_model(
    session: AsyncSession,
    model_name: str,
    version: str,
    redis_client: Optional[Any] = None,
) -> Optional[MLModel]:
    """Set specified model as active, retiring previously active models and invalidating cache."""
    # Find target model
    stmt = select(MLModel).where(MLModel.name == model_name, MLModel.version == version)
    res = await session.execute(stmt)
    target = res.scalar_one_or_none()

    if target is None:
        return None

    # Demote all existing active models to pending or archived
    await session.execute(
        update(MLModel)
        .where(MLModel.status == ModelStatus.ACTIVE.value)
        .values(status=ModelStatus.PENDING_APPROVAL.value)
    )

    # Promote target
    target.status = ModelStatus.ACTIVE.value
    await session.commit()

    # Invalidate Redis cache
    r = redis_client or default_redis_client
    if r is not None:
        try:
            await r.delete(ACTIVE_MODEL_CACHE_KEY)
        except Exception as e:
            logger.warning(f"Failed to invalidate Redis active model cache: {e}")

    return target
