"""Production billing provider adapters (EPIC-016).

Architecture only — no real payment execution. Adapters remain unavailable
until vendor credentials and webhook verification are configured.
"""

from __future__ import annotations

import os
from typing import Any

from enterprise.billing import (
    BillingPort,
    InvoiceSummary,
    NullBillingAdapter,
    SubscriptionSummary,
)
from enterprise.models import UNAVAILABLE_MESSAGES

__all__ = [
    "BILLING_PROVIDER_UNAVAILABLE",
    "PaddleBillingAdapter",
    "RazorpayBillingAdapter",
    "StripeBillingAdapter",
    "build_billing_adapter",
]

BILLING_PROVIDER_UNAVAILABLE = "Billing provider unavailable."


class _UnavailableBillingAdapter:
    """Shared honest-unavailable behaviour for vendor adapters."""

    provider: str = "null"

    def provider_name(self) -> str:
        return self.provider

    def is_available(self) -> bool:
        return False

    def get_subscription(self, org_id: str) -> SubscriptionSummary | None:
        _ = org_id
        return None

    def list_invoices(self, org_id: str) -> list[InvoiceSummary]:
        _ = org_id
        return []

    def payment_status(self, org_id: str) -> dict[str, Any]:
        return {
            "org_id": org_id,
            "available": False,
            "provider": self.provider_name(),
            "status": "unavailable",
            "message": BILLING_PROVIDER_UNAVAILABLE,
            "fallback_message": UNAVAILABLE_MESSAGES["billing"],
            "subscription": None,
            "invoices": [],
            "checkout_enabled": False,
            "webhooks_configured": False,
        }

    def create_checkout_session(self, org_id: str, *, plan: str | None = None) -> dict[str, Any]:
        _ = plan
        return {
            "ok": False,
            "org_id": org_id,
            "provider": self.provider_name(),
            "message": BILLING_PROVIDER_UNAVAILABLE,
        }

    def verify_webhook(self, payload: bytes, *, signature: str | None = None) -> dict[str, Any]:
        _ = payload, signature
        return {
            "ok": False,
            "provider": self.provider_name(),
            "verified": False,
            "message": BILLING_PROVIDER_UNAVAILABLE,
        }


class StripeBillingAdapter(_UnavailableBillingAdapter):
    """Stripe BillingPort — requires DSP_STRIPE_SECRET_KEY for live wiring."""

    provider = "stripe"

    def __init__(self, *, api_key: str | None = None, webhook_secret: str | None = None) -> None:
        self._api_key = (api_key or os.environ.get("DSP_STRIPE_SECRET_KEY") or "").strip()
        self._webhook_secret = (
            webhook_secret or os.environ.get("DSP_STRIPE_WEBHOOK_SECRET") or ""
        ).strip()

    def is_available(self) -> bool:
        # Never claim available without real SDK + verified credentials.
        return False

    def payment_status(self, org_id: str) -> dict[str, Any]:
        status = super().payment_status(org_id)
        status["credentials_present"] = bool(self._api_key)
        status["webhook_secret_present"] = bool(self._webhook_secret)
        return status


class RazorpayBillingAdapter(_UnavailableBillingAdapter):
    """Razorpay BillingPort — India-first commercial path (architecture)."""

    provider = "razorpay"

    def __init__(
        self,
        *,
        key_id: str | None = None,
        key_secret: str | None = None,
        webhook_secret: str | None = None,
    ) -> None:
        self._key_id = (key_id or os.environ.get("DSP_RAZORPAY_KEY_ID") or "").strip()
        self._key_secret = (
            key_secret or os.environ.get("DSP_RAZORPAY_KEY_SECRET") or ""
        ).strip()
        self._webhook_secret = (
            webhook_secret or os.environ.get("DSP_RAZORPAY_WEBHOOK_SECRET") or ""
        ).strip()

    def is_available(self) -> bool:
        return False

    def payment_status(self, org_id: str) -> dict[str, Any]:
        status = super().payment_status(org_id)
        status["credentials_present"] = bool(self._key_id and self._key_secret)
        status["webhook_secret_present"] = bool(self._webhook_secret)
        return status


class PaddleBillingAdapter(_UnavailableBillingAdapter):
    """Paddle BillingPort — global SaaS path (architecture)."""

    provider = "paddle"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        webhook_secret: str | None = None,
    ) -> None:
        self._api_key = (api_key or os.environ.get("DSP_PADDLE_API_KEY") or "").strip()
        self._webhook_secret = (
            webhook_secret or os.environ.get("DSP_PADDLE_WEBHOOK_SECRET") or ""
        ).strip()

    def is_available(self) -> bool:
        return False

    def payment_status(self, org_id: str) -> dict[str, Any]:
        status = super().payment_status(org_id)
        status["credentials_present"] = bool(self._api_key)
        status["webhook_secret_present"] = bool(self._webhook_secret)
        return status


def build_billing_adapter(provider: str | None = None) -> BillingPort:
    """Select billing adapter from env ``DSP_BILLING_PROVIDER`` (default null)."""
    name = (provider or os.environ.get("DSP_BILLING_PROVIDER") or "null").strip().lower()
    if name == "stripe":
        return StripeBillingAdapter()
    if name == "razorpay":
        return RazorpayBillingAdapter()
    if name == "paddle":
        return PaddleBillingAdapter()
    return NullBillingAdapter()


# Protocol satisfaction markers
_: tuple[BillingPort, BillingPort, BillingPort] = (
    StripeBillingAdapter(),
    RazorpayBillingAdapter(),
    PaddleBillingAdapter(),
)
