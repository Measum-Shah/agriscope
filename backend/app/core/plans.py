"""Plan entitlements, quota matrix, and enforcement dependencies."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, Optional

from fastapi import Depends

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.exceptions import ForbiddenException
from app.core.logging import logger
from app.models.user import User

try:
    import redis.asyncio as aioredis

    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None


@dataclass(frozen=True)
class PlanLimits:
    name: str
    max_predictions_per_day: int
    history_limit: Optional[int]
    max_fields: int
    batch_csv_enabled: bool
    batch_max_rows: int
    remote_sensing_enabled: bool
    forecast_enabled: bool
    model_comparison_enabled: bool
    explainability_enabled: bool
    export_enabled: bool
    api_keys_enabled: bool


PLAN_FREE = PlanLimits(
    name="free",
    max_predictions_per_day=30,
    history_limit=50,
    max_fields=1,
    batch_csv_enabled=False,
    batch_max_rows=0,
    remote_sensing_enabled=False,
    forecast_enabled=False,
    model_comparison_enabled=False,
    explainability_enabled=False,
    export_enabled=False,
    api_keys_enabled=False,
)

PLAN_PRO = PlanLimits(
    name="pro",
    max_predictions_per_day=1000,
    history_limit=None,  # unlimited
    max_fields=50,
    batch_csv_enabled=True,
    batch_max_rows=10000,
    remote_sensing_enabled=True,
    forecast_enabled=True,
    model_comparison_enabled=True,
    explainability_enabled=True,
    export_enabled=True,
    api_keys_enabled=True,
)

PLAN_ADMIN = PlanLimits(
    name="admin",
    max_predictions_per_day=100000,
    history_limit=None,
    max_fields=1000,
    batch_csv_enabled=True,
    batch_max_rows=50000,
    remote_sensing_enabled=True,
    forecast_enabled=True,
    model_comparison_enabled=True,
    explainability_enabled=True,
    export_enabled=True,
    api_keys_enabled=True,
)

PLANS: Dict[str, PlanLimits] = {
    "free": PLAN_FREE,
    "pro": PLAN_PRO,
    "admin": PLAN_ADMIN,
}


def get_plan_limits(plan_name: str) -> PlanLimits:
    """Returns limits for the specified plan, defaulting to free."""
    return PLANS.get(plan_name.lower(), PLAN_FREE)


class QuotaService:
    """Redis-backed daily prediction quota counter with in-memory fallback."""

    in_memory_usage: Dict[str, int] = defaultdict(int)

    @classmethod
    def _get_key(cls, user_id: str, date_str: Optional[str] = None) -> str:
        if not date_str:
            date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"quota:pred:{user_id}:{date_str}"

    @classmethod
    async def get_used_predictions_today(cls, user_id: str) -> int:
        key = cls._get_key(user_id)
        if redis_client:
            try:
                val = await redis_client.get(key)
                return int(val) if val else 0
            except Exception as e:
                logger.warning(f"Redis quota get failed, falling back to in-memory: {e}")
        return cls.in_memory_usage.get(key, 0)

    @classmethod
    async def increment_predictions_today(cls, user_id: str, count: int = 1) -> int:
        key = cls._get_key(user_id)
        if redis_client:
            try:
                pipe = redis_client.pipeline()
                pipe.incrby(key, count)
                # Expire in 48 hours to ensure day rollovers are clean
                pipe.expire(key, 172800)
                results = await pipe.execute()
                return int(results[0])
            except Exception as e:
                logger.warning(f"Redis quota incr failed, falling back to in-memory: {e}")
        cls.in_memory_usage[key] += count
        return cls.in_memory_usage[key]

    @classmethod
    def reset_memory_quota(cls) -> None:
        cls.in_memory_usage.clear()


def require_plan_feature(feature_attr: str) -> Callable:
    """FastAPI dependency enforcing that a user's plan has a given feature flag enabled."""

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        limits = get_plan_limits(current_user.plan)
        val = getattr(limits, feature_attr, False)
        if not val:
            raise ForbiddenException(
                detail=f"The '{feature_attr}' feature requires an upgraded subscription plan."
            )
        return current_user

    return dependency
