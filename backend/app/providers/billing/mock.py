"""Deterministic mock billing provider for offline development and test execution."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Set

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.core.logging import logger
from app.providers.billing.base import BillingProvider
from app.services.subscription_service import SubscriptionService


class MockBillingProvider(BillingProvider):
    """Offline, deterministic billing simulator."""

    def __init__(self):
        self._processed_events: Set[str] = set()

    async def create_checkout_session(
        self,
        user_id: str,
        email: str,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        session_id = f"cs_mock_{uuid.uuid4().hex[:12]}"
        url = f"{success_url}?session_id={session_id}&user_id={user_id}&plan={plan}"
        return {
            "session_id": session_id,
            "url": url,
            "provider": "mock",
        }

    async def create_customer_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> Dict[str, Any]:
        portal_url = f"{return_url}?portal_session=mock_{customer_id}"
        return {
            "url": portal_url,
            "provider": "mock",
        }

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature_header: str,
    ) -> Dict[str, Any]:
        if signature_header == "invalid_sig":
            raise BadRequestException("Invalid webhook signature")
        try:
            return json.loads(payload.decode("utf-8"))
        except Exception as e:
            raise BadRequestException(f"Failed to decode webhook payload: {e}")

    async def handle_webhook_event(
        self,
        event_payload: Dict[str, Any],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        event_id = event_payload.get("id", str(uuid.uuid4()))
        if event_id in self._processed_events:
            logger.info(f"Duplicate billing event ignored (idempotent): {event_id}")
            return {"status": "already_processed", "event_id": event_id}

        self._processed_events.add(event_id)

        event_type = event_payload.get("type", "")
        obj = event_payload.get("data", {}).get("object", {})

        user_id_str = obj.get("client_reference_id") or obj.get("metadata", {}).get("user_id")
        if not user_id_str:
            return {"status": "ignored_no_user", "event_id": event_id}

        user_id = uuid.UUID(user_id_str)

        if event_type in ("checkout.session.completed", "customer.subscription.created"):
            plan = obj.get("metadata", {}).get("plan", "pro")
            stripe_customer_id = obj.get("customer", "cus_mock_123")
            stripe_subscription_id = obj.get("subscription", "sub_mock_123")
            await SubscriptionService.transition_subscription(
                db=db,
                user_id=user_id,
                new_status="active",
                plan=plan,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
            )

        elif event_type in ("invoice.payment_succeeded", "customer.subscription.updated"):
            await SubscriptionService.transition_subscription(
                db=db,
                user_id=user_id,
                new_status="active",
                plan="pro",
            )

        elif event_type == "invoice.payment_failed":
            await SubscriptionService.transition_subscription(
                db=db,
                user_id=user_id,
                new_status="past_due",
                plan="pro",
            )

        elif event_type == "customer.subscription.deleted":
            await SubscriptionService.transition_subscription(
                db=db,
                user_id=user_id,
                new_status="canceled",
                plan="free",
            )

        return {"status": "handled", "event_id": event_id, "event_type": event_type}
