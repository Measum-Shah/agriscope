"""Abstract interface for payment and subscription providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession


class BillingProvider(ABC):
    """Abstract interface defining required billing operations."""

    @abstractmethod
    async def create_checkout_session(
        self,
        user_id: str,
        email: str,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        """Initiates an external checkout session for plan upgrade."""
        pass

    @abstractmethod
    async def create_customer_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> Dict[str, Any]:
        """Generates self-service customer portal session URL."""
        pass

    @abstractmethod
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature_header: str,
    ) -> Dict[str, Any]:
        """Cryptographically verifies incoming webhook signature."""
        pass

    @abstractmethod
    async def handle_webhook_event(
        self,
        event_payload: Dict[str, Any],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Processes event idempotently and transitions subscription state."""
        pass
