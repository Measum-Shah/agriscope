"""Pydantic schemas for API key management and usage tracking."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_SCOPES = [
    "predict:read",
    "predict:write",
    "batch:read",
    "batch:write",
    "weather:read",
    "fields:read",
]


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Descriptive label for this API key")
    scopes: List[str] = Field(default=DEFAULT_SCOPES, description="List of access scopes granted to this key")
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=365, description="Optional lifespan in days")
    rate_limit_per_min: Optional[int] = Field(default=60, ge=1, le=10000, description="Rate limit per minute")


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    key_prefix: str
    scopes: List[str]
    rate_limit_per_min: int
    is_active: bool
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime


class ApiKeyCreatedResponse(ApiKeyResponse):
    raw_key: str = Field(..., description="Full secret API key string. Shown only once upon creation.")


class ApiKeyUsageStats(BaseModel):
    key_id: uuid.UUID
    name: str
    requests_today: int
    requests_this_week: int
    endpoints_breakdown: Dict[str, int]
    errors_breakdown: Dict[str, int]
