"""Stripe payment provider supporting checkout, portal sessions, and webhook signatures."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Set

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestException
from app.core.logging import logger
from app.providers.billing.base import BillingProvider
from app.services.subscription_service import SubscriptionService


class StripeProvider(BillingProvider):
    """Production and test-mode Stripe billing provider."""

    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self._processed_events: Set[str] = set()

    async def create_checkout_session(
        self,
        user_id: str,
        email: str,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        try:
            session = stripe.checkout.Session.create(
                customer_email=email,
                client_reference_id=user_id,
                payment_method_types=["card"],
                mode="subscription",
                line_items=[{"price": settings.STRIPE_PRICE_ID_PRO, "quantity": 1}],
                metadata={"user_id": user_id, "plan": plan},
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return {"session_id": session.id, "url": session.url, "provider": "stripe"}
        except Exception as e:
            logger.error(f"Stripe checkout session creation failed: {e}")
            raise BadRequestException(f"Stripe checkout error: {e}")

    async def create_customer_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> Dict[str, Any]:
        try:
            portal = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return {"url": portal.url, "provider": "stripe"}
        except Exception as e:
            logger.error(f"Stripe portal session creation failed: {e}")
            raise BadRequestException(f"Stripe portal error: {e}")

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature_header: str,
    ) -> Dict[str, Any]:
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature_header,
                secret=settings.STRIPE_WEBHOOK_SECRET,
            )
            return event
        except stripe.error.SignatureVerificationError as e:
            logger.warning(f"Stripe signature verification failed: {e}")
            raise BadRequestException("Invalid Stripe webhook signature")
        except Exception as e:
            raise BadRequestException(f"Failed to parse Stripe event: {e}")

    async def handle_webhook_event(
        self,
        event_payload: Dict[str, Any],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        event_id = event_payload.get("id", "")
        if event_id in self._processed_events:
            logger.info(f"Duplicate Stripe event {event_id} ignored (idempotent)")
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
            stripe_customer_id = obj.get("customer")
            stripe_subscription_id = obj.get("subscription")
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
