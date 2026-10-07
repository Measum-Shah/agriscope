"""Billing router: Stripe and Mock checkout sessions, customer portal, and webhooks."""

from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import BadRequestException
from app.core.plans import get_plan_limits
from app.db.session import get_db
from app.models.user import User
from app.providers.billing import get_billing_provider
from app.schemas.billing import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    PortalSessionResponse,
    SubscriptionInfoResponse,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/billing", tags=["Billing & Subscriptions"])


@router.get(
    "/subscription",
    response_model=SubscriptionInfoResponse,
    summary="Get current user subscription details",
)
async def get_subscription_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionInfoResponse:
    sub = await SubscriptionService.get_or_create_subscription(db, current_user.id)
    limits = get_plan_limits(current_user.plan)

    return SubscriptionInfoResponse(
        plan=current_user.plan,
        status=sub.status,
        is_active=(sub.status == "active" or current_user.plan in ("pro", "admin")),
        stripe_customer_id=sub.stripe_customer_id,
        current_period_end=sub.current_period_end,
        max_predictions_per_day=limits.max_predictions_per_day,
        max_fields=limits.max_fields,
        api_keys_enabled=limits.api_keys_enabled,
        batch_csv_enabled=limits.batch_csv_enabled,
        remote_sensing_enabled=limits.remote_sensing_enabled,
    )


@router.post(
    "/checkout",
    response_model=CheckoutSessionResponse,
    summary="Initiate checkout session for subscription upgrade",
)
async def create_checkout(
    payload: CheckoutSessionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> CheckoutSessionResponse:
    base_url = str(request.base_url).rstrip("/")
    success_url = payload.success_url or f"{base_url}/settings/billing?checkout=success"
    cancel_url = payload.cancel_url or f"{base_url}/settings/billing?checkout=cancel"

    provider = get_billing_provider()
    session_data = await provider.create_checkout_session(
        user_id=str(current_user.id),
        email=current_user.email,
        plan=payload.plan,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return CheckoutSessionResponse(
        session_id=session_data["session_id"],
        url=session_data["url"],
        provider=session_data.get("provider", "mock"),
    )


@router.post(
    "/portal",
    response_model=PortalSessionResponse,
    summary="Create Stripe customer portal session",
)
async def create_customer_portal(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalSessionResponse:
    sub = await SubscriptionService.get_or_create_subscription(db, current_user.id)
    customer_id = sub.stripe_customer_id or f"cus_mock_{current_user.id}"
    base_url = str(request.base_url).rstrip("/")
    return_url = f"{base_url}/settings/billing"

    provider = get_billing_provider()
    portal_data = await provider.create_customer_portal_session(
        customer_id=customer_id,
        return_url=return_url,
    )
    return PortalSessionResponse(
        url=portal_data["url"],
        provider=portal_data.get("provider", "mock"),
    )


@router.post(
    "/webhook",
    summary="Stripe payment webhook endpoint",
)
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    payload_bytes = await request.body()
    provider = get_billing_provider()

    event = provider.verify_webhook_signature(
        payload=payload_bytes,
        signature_header=stripe_signature or "mock_sig",
    )
    return await provider.handle_webhook_event(event, db)


@router.post(
    "/mock/upgrade",
    response_model=SubscriptionInfoResponse,
    summary="Instant mock upgrade to Pro plan (Dev / Test / Demo)",
)
async def mock_upgrade_plan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionInfoResponse:
    sub, user = await SubscriptionService.transition_subscription(
        db=db,
        user_id=current_user.id,
        new_status="active",
        plan="pro",
        stripe_customer_id=f"cus_mock_{current_user.id}",
        stripe_subscription_id=f"sub_mock_{current_user.id}",
    )
    limits = get_plan_limits(user.plan)
    return SubscriptionInfoResponse(
        plan=user.plan,
        status=sub.status,
        is_active=True,
        stripe_customer_id=sub.stripe_customer_id,
        current_period_end=sub.current_period_end,
        max_predictions_per_day=limits.max_predictions_per_day,
        max_fields=limits.max_fields,
        api_keys_enabled=limits.api_keys_enabled,
        batch_csv_enabled=limits.batch_csv_enabled,
        remote_sensing_enabled=limits.remote_sensing_enabled,
    )


@router.post(
    "/mock/downgrade",
    response_model=SubscriptionInfoResponse,
    summary="Instant mock downgrade to Free plan (Dev / Test / Demo)",
)
async def mock_downgrade_plan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionInfoResponse:
    sub, user = await SubscriptionService.transition_subscription(
        db=db,
        user_id=current_user.id,
        new_status="canceled",
        plan="free",
    )
    limits = get_plan_limits(user.plan)
    return SubscriptionInfoResponse(
        plan=user.plan,
        status=sub.status,
        is_active=False,
        stripe_customer_id=sub.stripe_customer_id,
        current_period_end=sub.current_period_end,
        max_predictions_per_day=limits.max_predictions_per_day,
        max_fields=limits.max_fields,
        api_keys_enabled=limits.api_keys_enabled,
        batch_csv_enabled=limits.batch_csv_enabled,
        remote_sensing_enabled=limits.remote_sensing_enabled,
    )
