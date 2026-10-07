"""Subscription lifecycle state machine managing plans, audit trails, and user notifications."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.models.subscription import Subscription
from app.models.user import User
from app.services.notification_service import SSEConnectionManager


class SubscriptionService:
    """Manages subscription state transitions (free -> pro -> past_due -> canceled)."""

    VALID_STATUSES = {"active", "past_due", "canceled", "incomplete"}

    @classmethod
    async def get_or_create_subscription(
        cls, db: AsyncSession, user_id: uuid.UUID
    ) -> Subscription:
        query = select(Subscription).where(Subscription.user_id == user_id)
        result = await db.execute(query)
        sub = result.scalar_one_or_none()
        if not sub:
            sub = Subscription(
                user_id=user_id,
                plan="free",
                status="canceled",
            )
            db.add(sub)
            await db.commit()
            await db.refresh(sub)
        return sub

    @classmethod
    async def transition_subscription(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        new_status: str,
        plan: str = "pro",
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> Tuple[Subscription, User]:
        """Applies state transition, updates User.plan, records audit trail, and issues notification."""
        user = await db.get(User, user_id)
        if not user:
            raise NotFoundException("User not found for subscription transition")

        sub = await cls.get_or_create_subscription(db, user_id)
        old_status = sub.status
        old_plan = user.plan

        sub.status = new_status
        if stripe_customer_id:
            sub.stripe_customer_id = stripe_customer_id
        if stripe_subscription_id:
            sub.stripe_subscription_id = stripe_subscription_id
        if period_start:
            sub.current_period_start = period_start
        if period_end:
            sub.current_period_end = period_end

        notif_title = ""
        notif_message = ""
        notif_type = "info"
        audit_action = f"subscription.{new_status}"

        if new_status == "active":
            user.plan = plan
            sub.plan = plan
            notif_title = f"Subscription Upgraded to {plan.title()}"
            notif_message = f"Your AgriScope account is now on {plan.title()}. Quotas, satellite indices, and API keys are active."
            notif_type = "info"
            audit_action = "subscription.upgraded"

        elif new_status == "past_due":
            # Retain plan temporarily during grace period, but alert user
            notif_title = "Subscription Payment Past Due"
            notif_message = "Your latest renewal payment failed. Please update your payment method to maintain Pro access."
            notif_type = "warning"
            audit_action = "subscription.past_due"

        elif new_status in ("canceled", "incomplete_expired"):
            user.plan = "free"
            sub.plan = "free"
            notif_title = "Subscription Canceled"
            notif_message = "Your subscription has been canceled. Your account has reverted to the Free plan."
            notif_type = "alert"
            audit_action = "subscription.canceled"

        # Record audit log entry
        audit_log = AuditLog(
            actor="billing_service",
            action=audit_action,
            target=str(user.id),
            metadata_json={
                "old_status": old_status,
                "new_status": new_status,
                "old_plan": old_plan,
                "new_plan": user.plan,
                "stripe_customer_id": stripe_customer_id,
            },
        )
        db.add(audit_log)

        # Dispatch in-app notification
        notification = Notification(
            user_id=user.id,
            title=notif_title,
            message=notif_message,
            type=notif_type,
            metadata_json={"plan": user.plan, "status": new_status},
        )
        db.add(notification)

        await db.commit()
        await db.refresh(sub)
        await db.refresh(user)

        # Broadcast SSE live push
        try:
            await SSEConnectionManager.broadcast_to_user(
                user_id=user.id,
                event_type="subscription_updated",
                payload={
                    "plan": user.plan,
                    "status": new_status,
                    "title": notif_title,
                    "message": notif_message,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to push SSE subscription event: {e}")

        logger.info(
            f"User {user.email} transitioned subscription from {old_status}({old_plan}) -> {new_status}({user.plan})"
        )
        return sub, user
