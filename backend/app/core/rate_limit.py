"""Rate limiting engine backed by Redis with in-memory fallback."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable, Dict, List

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import AgriScopeException, RateLimitExceededException
from app.core.logging import logger

try:
    import redis.asyncio as aioredis

    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None


class RateLimiter:
    """Sliding-window rate limiter utilizing Redis if available or in-memory fallback."""

    in_memory_history: Dict[str, List[float]] = defaultdict(list)

    def __init__(self, requests_per_minute: int = 60, prefix: str = "rl"):
        self.requests_per_minute = requests_per_minute
        self.prefix = prefix

    @classmethod
    def reset_memory(cls) -> None:
        cls.in_memory_history.clear()

    async def check_rate_limit(self, identifier: str) -> None:
        key = f"{self.prefix}:{identifier}"
        now = time.time()
        window_start = now - 60.0

        import os
        if redis_client and os.environ.get("ENVIRONMENT") != "testing":
            try:
                # Redis sliding window with sorted sets
                pipe = redis_client.pipeline()
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zadd(key, {str(now): now})
                pipe.zcard(key)
                pipe.expire(key, 65)
                _, _, count, _ = await pipe.execute()

                if count > self.requests_per_minute:
                    raise RateLimitExceededException(
                        detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute.",
                        retry_after=60,
                    )
                return
            except AgriScopeException:
                raise
            except Exception as e:
                logger.warning(f"Redis rate limiter failed, falling back to memory: {e}")

        # In-memory fallback
        timestamps = self.in_memory_history[key]
        self.in_memory_history[key] = [t for t in timestamps if t > window_start]
        if len(self.in_memory_history[key]) >= self.requests_per_minute:
            oldest = self.in_memory_history[key][0] if self.in_memory_history[key] else window_start
            retry_after = max(1, int(60 - (now - oldest)))
            raise RateLimitExceededException(
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute.",
                retry_after=retry_after,
            )
        self.in_memory_history[key].append(now)


def create_rate_limiter(requests_per_minute: int = 60, prefix: str = "rl") -> Callable:
    """Factory creating a FastAPI dependency enforcing route-level rate limits."""
    limiter = RateLimiter(requests_per_minute=requests_per_minute, prefix=prefix)

    async def dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        # Combine IP and path for route isolation
        identifier = f"{request.url.path}:{client_ip}"
        await limiter.check_rate_limit(identifier)

    return dependency
