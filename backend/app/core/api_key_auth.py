"""FastAPI dependencies for API Key authentication, rate limiting, and scope enforcement."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Callable, List, Optional

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import ForbiddenException, QuotaExceededException, UnauthorizedException
from app.core.plans import QuotaService, get_plan_limits
from app.core.rate_limit import RateLimiter
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.services.api_key_service import ApiKeyService, ApiKeyUsageTracker


async def get_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    """Extracts, hashes, and validates caller's API key, enforcing rate limits and quotas."""
    raw_key: Optional[str] = None
    if x_api_key:
        raw_key = x_api_key.strip()
    elif authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[1].startswith("agri_"):
            raw_key = parts[1]
        elif len(parts) == 1 and parts[0].startswith("agri_"):
            raw_key = parts[0]

    if not raw_key:
        raise UnauthorizedException(detail="API Key missing. Provide via 'X-API-Key' header.")

    hashed = ApiKeyService.hash_key(raw_key)
    query = select(ApiKey).where(ApiKey.hashed_key == hashed)
    result = await db.execute(query)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise UnauthorizedException(detail="Invalid API key.")

    if not api_key.is_active:
        raise UnauthorizedException(detail="API key has been revoked.")

    if api_key.expires_at:
        now_utc = datetime.now(timezone.utc)
        exp_utc = api_key.expires_at if api_key.expires_at.tzinfo else api_key.expires_at.replace(tzinfo=timezone.utc)
        if exp_utc < now_utc:
            raise UnauthorizedException(detail="API key has expired.")

    # Load owner user
    user = await db.get(User, api_key.user_id)
    if not user or user.status != "active":
        raise ForbiddenException(detail="Account associated with this API key is inactive.")

    # Per-key rate limiting (Redis sliding window / memory fallback)
    limiter = RateLimiter(requests_per_minute=api_key.rate_limit_per_min, prefix="rl:key")
    await limiter.check_rate_limit(str(api_key.id))

    # Daily user prediction quota check
    limits = get_plan_limits(user.plan)
    used = await QuotaService.get_used_predictions_today(str(user.id))
    if used >= limits.max_predictions_per_day:
        raise QuotaExceededException(
            detail=f"Daily prediction quota exhausted ({used}/{limits.max_predictions_per_day}). Upgrade plan for higher limits."
        )

    # Touch last_used_at and track endpoint usage
    api_key.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    endpoint = request.url.path
    await ApiKeyUsageTracker.record_hit(str(api_key.id), endpoint, 200)

    request.state.api_key = api_key
    request.state.api_user = user
    return api_key


def require_api_key_scope(required_scopes: List[str]) -> Callable:
    """Dependency verifying that the authenticated API key contains all required scopes."""

    async def scope_checker(api_key: ApiKey = Depends(get_api_key)) -> ApiKey:
        key_scopes = set(api_key.scope_list)
        for scope in required_scopes:
            if scope not in key_scopes:
                raise ForbiddenException(detail=f"API key missing required scope: '{scope}'.")
        return api_key

    return scope_checker


async def get_api_key_or_user(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Accepts either API Key or JWT Bearer token and returns authenticated User."""
    has_api_key = bool(x_api_key) or (bool(authorization) and "agri_" in authorization)
    if has_api_key:
        api_key = await get_api_key(
            request=request, x_api_key=x_api_key, authorization=authorization, db=db
        )
        user = await db.get(User, api_key.user_id)
        if not user:
            raise UnauthorizedException(detail="API key owner not found.")
        return user

    # Fallback to standard JWT bearer token authentication
    return await get_current_user(user_id=await get_current_user_id(authorization), db=db)


async def get_current_user_id(authorization: Optional[str]) -> Any:
    from app.core.deps import get_current_user_id as _get_id
    return await _get_id(authorization)
