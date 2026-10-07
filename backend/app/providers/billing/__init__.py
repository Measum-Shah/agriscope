"""Billing provider factory resolving Stripe or Mock providers."""

from __future__ import annotations

from app.core.config import settings
from app.providers.billing.base import BillingProvider
from app.providers.billing.mock import MockBillingProvider
from app.providers.billing.stripe import StripeProvider

_mock_instance: MockBillingProvider | None = None
_stripe_instance: StripeProvider | None = None


def get_billing_provider() -> BillingProvider:
    global _mock_instance, _stripe_instance
    provider_name = settings.BILLING_PROVIDER.lower()
    if provider_name == "stripe" and settings.STRIPE_SECRET_KEY:
        if _stripe_instance is None:
            _stripe_instance = StripeProvider()
        return _stripe_instance
    else:
        if _mock_instance is None:
            _mock_instance = MockBillingProvider()
        return _mock_instance
