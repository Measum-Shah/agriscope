"""REST API endpoints for API Key provisioning, revocation, and usage statistics."""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.plans import require_plan_feature
from app.db.session import get_db
from app.models.user import User
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    ApiKeyUsageStats,
)
from app.services.api_key_service import ApiKeyService

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


@router.post(
    "",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key (shown once)",
)
async def create_api_key(
    payload: ApiKeyCreate,
    current_user: User = Depends(require_plan_feature("api_keys_enabled")),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreatedResponse:
    """Provisions a new API key with configured scopes. Secret key is only returned in this response."""
    api_key, raw_key = await ApiKeyService.create_key(db, current_user, payload)
    return ApiKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scope_list,
        rate_limit_per_min=api_key.rate_limit_per_min,
        is_active=api_key.is_active,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        raw_key=raw_key,
    )


@router.get(
    "",
    response_model=List[ApiKeyResponse],
    summary="List all API keys for the current user",
)
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ApiKeyResponse]:
    """Returns active and inactive API keys without secret key strings."""
    keys = await ApiKeyService.list_keys(db, current_user.id)
    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            scopes=k.scope_list,
            rate_limit_per_min=k.rate_limit_per_min,
            is_active=k.is_active,
            expires_at=k.expires_at,
            last_used_at=k.last_used_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.post(
    "/{key_id}/revoke",
    response_model=ApiKeyResponse,
    summary="Revoke an existing API key",
)
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    """Revokes the given API key, rendering it unusable for future requests."""
    k = await ApiKeyService.revoke_key(db, current_user.id, key_id)
    return ApiKeyResponse(
        id=k.id,
        name=k.name,
        key_prefix=k.key_prefix,
        scopes=k.scope_list,
        rate_limit_per_min=k.rate_limit_per_min,
        is_active=k.is_active,
        expires_at=k.expires_at,
        last_used_at=k.last_used_at,
        created_at=k.created_at,
    )


@router.delete(
    "/{key_id}",
    summary="Revoke and disable API key",
)
async def delete_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await ApiKeyService.revoke_key(db, current_user.id, key_id)
    return {"status": "revoked", "id": str(key_id)}


@router.get(
    "/{key_id}/usage",
    response_model=ApiKeyUsageStats,
    summary="Get API key usage statistics",
)
async def get_api_key_usage(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyUsageStats:
    """Returns requests count today/this week and breakdown by endpoints & error codes."""
    return await ApiKeyService.get_usage_stats(db, current_user.id, key_id)
