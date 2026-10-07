"""Unit tests for Billing providers, checkout sessions, webhooks, and subscription state machine."""

from __future__ import annotations

import json
import uuid
import pytest
from httpx import AsyncClient

from app.core.plans import get_plan_limits
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.models.subscription import Subscription
from app.models.user import User
from app.providers.billing.mock import MockBillingProvider
from app.providers.billing.stripe import StripeProvider
from app.services.subscription_service import SubscriptionService


@pytest.mark.asyncio
async def test_checkout_and_customer_portal_sessions(client: AsyncClient):
    """Verifies checkout session and customer portal URL generation."""
    # Register test user
    await client.post(
        "/api/v1/auth/register",
        json={"email": "bill_user@agriscope.io", "password": "SecurePassword123!", "name": "Billing User"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "bill_user@agriscope.io", "password": "SecurePassword123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Checkout session
    checkout_res = await client.post(
        "/api/v1/billing/checkout",
        json={"plan": "pro"},
        headers=headers,
    )
    assert checkout_res.status_code == 200
    c_data = checkout_res.json()
    assert "url" in c_data
    assert "session_id" in c_data

    # Portal session
    portal_res = await client.post("/api/v1/billing/portal", headers=headers)
    assert portal_res.status_code == 200
    p_data = portal_res.json()
    assert "url" in p_data


@pytest.mark.asyncio
async def test_subscription_state_machine_affects_entitlements_immediately(client: AsyncClient):
    """Verifies free -> pro -> past_due -> canceled updates User.plan and entitlements in real-time."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "state_machine@agriscope.io", "password": "SecurePassword123!", "name": "State Machine"},
    )
    user_id = reg.json()["id"]

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "state_machine@agriscope.io", "password": "SecurePassword123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # 1. Initially FREE
    sub_info = await client.get("/api/v1/billing/subscription", headers=headers)
    assert sub_info.status_code == 200
    assert sub_info.json()["plan"] == "free"
    assert sub_info.json()["api_keys_enabled"] is False

    # Pro feature forbidden
    key_attempt = await client.post("/api/v1/api-keys", json={"name": "K1"}, headers=headers)
    assert key_attempt.status_code == 403

    # 2. Upgrade to PRO
    upgrade_res = await client.post("/api/v1/billing/mock/upgrade", headers=headers)
    assert upgrade_res.status_code == 200
    assert upgrade_res.json()["plan"] == "pro"
    assert upgrade_res.json()["api_keys_enabled"] is True

    # Entitlements unlocked immediately
    key_success = await client.post("/api/v1/api-keys", json={"name": "K1"}, headers=headers)
    assert key_success.status_code == 201

    # 3. Simulate transition to PAST_DUE
    app_engine = client._transport.app.state.test_engine
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    session_factory = async_sessionmaker(bind=app_engine, class_=AsyncSession)
    async with session_factory() as db:
        await SubscriptionService.transition_subscription(
            db=db,
            user_id=uuid.UUID(user_id),
            new_status="past_due",
            plan="pro",
        )

    sub_past_due = await client.get("/api/v1/billing/subscription", headers=headers)
    assert sub_past_due.json()["status"] == "past_due"

    # 4. Downgrade / Cancel -> reverts to FREE
    downgrade_res = await client.post("/api/v1/billing/mock/downgrade", headers=headers)
    assert downgrade_res.status_code == 200
    assert downgrade_res.json()["plan"] == "free"
    assert downgrade_res.json()["api_keys_enabled"] is False

    # Pro feature locked again immediately
    key_attempt2 = await client.post("/api/v1/api-keys", json={"name": "K2"}, headers=headers)
    assert key_attempt2.status_code == 403


@pytest.mark.asyncio
async def test_webhook_signature_and_idempotent_event_handling(client: AsyncClient):
    """Verifies webhook signature verification and idempotent event processing."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "webhook_user@agriscope.io", "password": "SecurePassword123!", "name": "Webhook User"},
    )
    user_id = reg.json()["id"]

    event_id = f"evt_test_{uuid.uuid4().hex[:12]}"
    event_payload = {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "client_reference_id": user_id,
                "customer": "cus_stripe_abc123",
                "subscription": "sub_stripe_xyz789",
                "metadata": {"user_id": user_id, "plan": "pro"},
            }
        },
    }
    payload_bytes = json.dumps(event_payload).encode("utf-8")

    # 1. Invalid signature -> 400 Bad Request
    bad_res = await client.post(
        "/api/v1/billing/webhook",
        content=payload_bytes,
        headers={"Stripe-Signature": "invalid_sig", "Content-Type": "application/json"},
    )
    assert bad_res.status_code == 400

    # 2. Valid signature -> processed
    ok_res = await client.post(
        "/api/v1/billing/webhook",
        content=payload_bytes,
        headers={"Stripe-Signature": "valid_test_sig", "Content-Type": "application/json"},
    )
    assert ok_res.status_code == 200
    assert ok_res.json()["status"] == "handled"

    # 3. Duplicate event with same ID -> idempotent ignored
    dup_res = await client.post(
        "/api/v1/billing/webhook",
        content=payload_bytes,
        headers={"Stripe-Signature": "valid_test_sig", "Content-Type": "application/json"},
    )
    assert dup_res.status_code == 200
    assert dup_res.json()["status"] == "already_processed"
