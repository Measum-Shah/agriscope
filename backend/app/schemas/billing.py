"""Pydantic schemas for checkout sessions, portal redirects, and subscription status."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CheckoutSessionRequest(BaseModel):
    plan: str = Field("pro", description="Target subscription plan (e.g., 'pro')")
    success_url: Optional[str] = Field(None, description="Redirect URL upon checkout completion")
    cancel_url: Optional[str] = Field(None, description="Redirect URL upon cancellation")


class CheckoutSessionResponse(BaseModel):
    session_id: str
    url: str
    provider: str


class PortalSessionResponse(BaseModel):
    url: str
    provider: str


class SubscriptionInfoResponse(BaseModel):
    plan: str
    status: str
    is_active: bool
    stripe_customer_id: Optional[str] = None
    current_period_end: Optional[datetime] = None
    max_predictions_per_day: int
    max_fields: int
    api_keys_enabled: bool
    batch_csv_enabled: bool
    remote_sensing_enabled: bool
