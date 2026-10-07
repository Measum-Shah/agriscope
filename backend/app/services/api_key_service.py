"""API Key management service: creation, hashing at rest, revocation, and usage tracking."""

from __future__ import annotations

import hashlib
import secrets
import uuid
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate, ApiKeyUsageStats

try:
    import redis.asyncio as aioredis

    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None


class ApiKeyUsageTracker:
    """Tracks endpoint invocations and error tallies in Redis with in-memory fallback."""

    # Fallback memory structures: key_id -> metric -> count
    _memory_daily: Dict[str, int] = defaultdict(int)
    _memory_weekly: Dict[str, int] = defaultdict(int)
    _memory_endpoints: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    _memory_errors: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    @classmethod
    async def record_hit(cls, key_id: str, endpoint: str, status_code: int) -> None:
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y%m%d")
        week = now.strftime("%Y%W")

        if redis_client and os.environ.get("ENVIRONMENT") != "testing":
            try:
                pipe = redis_client.pipeline()
                pipe.incr(f"usage:key:{key_id}:day:{today}")
                pipe.expire(f"usage:key:{key_id}:day:{today}", 86400 * 2)
                pipe.incr(f"usage:key:{key_id}:week:{week}")
                pipe.expire(f"usage:key:{key_id}:week:{week}", 86400 * 14)
                pipe.hincrby(f"usage:key:{key_id}:endpoints", endpoint, 1)
                pipe.expire(f"usage:key:{key_id}:endpoints", 86400 * 30)
                if status_code >= 400:
                    pipe.hincrby(f"usage:key:{key_id}:errors", str(status_code), 1)
                    pipe.expire(f"usage:key:{key_id}:errors", 86400 * 30)
                await pipe.execute()
                return
            except Exception as e:
                logger.warning(f"Redis API key usage tracking fallback: {e}")

        # In-memory fallback
        cls._memory_daily[f"{key_id}:{today}"] += 1
        cls._memory_weekly[f"{key_id}:{week}"] += 1
        cls._memory_endpoints[key_id][endpoint] += 1
        if status_code >= 400:
            cls._memory_errors[key_id][str(status_code)] += 1

    @classmethod
    async def get_stats(cls, key_id: str, key_name: str) -> ApiKeyUsageStats:
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y%m%d")
        week = now.strftime("%Y%W")

        requests_today = 0
        requests_this_week = 0
        endpoints_breakdown: Dict[str, int] = {}
        errors_breakdown: Dict[str, int] = {}

        if redis_client and os.environ.get("ENVIRONMENT") != "testing":
            try:
                pipe = redis_client.pipeline()
                pipe.get(f"usage:key:{key_id}:day:{today}")
                pipe.get(f"usage:key:{key_id}:week:{week}")
                pipe.hgetall(f"usage:key:{key_id}:endpoints")
                pipe.hgetall(f"usage:key:{key_id}:errors")
                results = await pipe.execute()

                requests_today = int(results[0]) if results[0] else 0
                requests_this_week = int(results[1]) if results[1] else 0
                endpoints_breakdown = {k: int(v) for k, v in (results[2] or {}).items()}
                errors_breakdown = {k: int(v) for k, v in (results[3] or {}).items()}
                return ApiKeyUsageStats(
                    key_id=uuid.UUID(key_id),
                    name=key_name,
                    requests_today=requests_today,
                    requests_this_week=requests_this_week,
                    endpoints_breakdown=endpoints_breakdown,
                    errors_breakdown=errors_breakdown,
                )
            except Exception as e:
                logger.warning(f"Redis get_stats failed, using memory fallback: {e}")

        requests_today = cls._memory_daily.get(f"{key_id}:{today}", 0)
        requests_this_week = cls._memory_weekly.get(f"{key_id}:{week}", 0)
        endpoints_breakdown = dict(cls._memory_endpoints.get(key_id, {}))
        errors_breakdown = dict(cls._memory_errors.get(key_id, {}))

        return ApiKeyUsageStats(
            key_id=uuid.UUID(key_id),
            name=key_name,
            requests_today=requests_today,
            requests_this_week=requests_this_week,
            endpoints_breakdown=endpoints_breakdown,
            errors_breakdown=errors_breakdown,
        )


class ApiKeyService:
    @staticmethod
    def hash_key(raw_key: str) -> str:
        """Deterministic SHA-256 digest stored at rest."""
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    async def create_key(
        cls, db: AsyncSession, user: User, payload: ApiKeyCreate
    ) -> Tuple[ApiKey, str]:
        """Generates random high-entropy token, records prefix & hash, returns raw token once."""
        random_entropy = secrets.token_hex(20)
        raw_key = f"agri_live_{random_entropy}"
        key_prefix = raw_key[:12]
        hashed_key = cls.hash_key(raw_key)

        expires_at = None
        if payload.expires_in_days:
            from datetime import timedelta
            expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)

        scopes_str = ",".join(payload.scopes)

        api_key = ApiKey(
            user_id=user.id,
            name=payload.name,
            key_prefix=key_prefix,
            hashed_key=hashed_key,
            scopes=scopes_str,
            rate_limit_per_min=payload.rate_limit_per_min or 60,
            is_active=True,
            expires_at=expires_at,
        )
        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)
        return api_key, raw_key

    @classmethod
    async def list_keys(cls, db: AsyncSession, user_id: uuid.UUID) -> List[ApiKey]:
        """Returns all keys owned by the user, newest first."""
        query = (
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(desc(ApiKey.created_at))
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @classmethod
    async def get_key_by_id(
        cls, db: AsyncSession, user_id: uuid.UUID, key_id: uuid.UUID
    ) -> ApiKey:
        query = select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
        result = await db.execute(query)
        api_key = result.scalar_one_or_none()
        if not api_key:
            raise NotFoundException("API key not found")
        return api_key

    @classmethod
    async def revoke_key(
        cls, db: AsyncSession, user_id: uuid.UUID, key_id: uuid.UUID
    ) -> ApiKey:
        """Sets is_active=False on the target key."""
        api_key = await cls.get_key_by_id(db, user_id, key_id)
        api_key.is_active = False
        await db.commit()
        await db.refresh(api_key)
        return api_key

    @classmethod
    async def get_usage_stats(
        cls, db: AsyncSession, user_id: uuid.UUID, key_id: uuid.UUID
    ) -> ApiKeyUsageStats:
        api_key = await cls.get_key_by_id(db, user_id, key_id)
        return await ApiKeyUsageTracker.get_stats(str(api_key.id), api_key.name)
