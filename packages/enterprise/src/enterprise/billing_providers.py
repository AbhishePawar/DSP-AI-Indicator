"""Production billing provider adapters (EPIC-016 + Razorpay live path).

Stripe and Paddle remain honest-unavailable. Razorpay is live only when
key_id, key_secret, and webhook_secret are configured and order/webhook
verification is implemented — never by flipping a flag.
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
from enterprise.razorpay_http import (
    DEFAULT_RAZORPAY_API_BASE,
    RazorpayHttpClient,
    RazorpayRequestError,
    UrllibRazorpayHttpClient,
    checkout_signature,
    signatures_match,
    webhook_signature,
)

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

    def create_checkout_session(
        self, org_id: str, *, plan: str | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        _ = plan, kwargs
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

    def verify_checkout_signature(
        self, *, order_id: str, payment_id: str, signature: str
    ) -> dict[str, Any]:
        _ = order_id, payment_id, signature
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
    """Razorpay BillingPort — live orders + HMAC verification when configured."""

    provider = "razorpay"

    def __init__(
        self,
        *,
        key_id: str | None = None,
        key_secret: str | None = None,
        webhook_secret: str | None = None,
        http_client: RazorpayHttpClient | None = None,
        api_base: str | None = None,
    ) -> None:
        self._key_id = (key_id or os.environ.get("DSP_RAZORPAY_KEY_ID") or "").strip()
        self._key_secret = (
            key_secret or os.environ.get("DSP_RAZORPAY_KEY_SECRET") or ""
        ).strip()
        self._webhook_secret = (
            webhook_secret or os.environ.get("DSP_RAZORPAY_WEBHOOK_SECRET") or ""
        ).strip()
        self._http_client = http_client
        self._api_base = (
            api_base
            or os.environ.get("DSP_RAZORPAY_API_BASE")
            or DEFAULT_RAZORPAY_API_BASE
        ).rstrip("/")

    def is_available(self) -> bool:
        return bool(self._key_id and self._key_secret and self._webhook_secret)

    def _client(self) -> RazorpayHttpClient | None:
        if self._http_client is not None:
            return self._http_client
        if not self._key_id or not self._key_secret:
            return None
        return UrllibRazorpayHttpClient(
            key_id=self._key_id,
            key_secret=self._key_secret,
            base_url=self._api_base,
        )

    def payment_status(self, org_id: str) -> dict[str, Any]:
        if not self.is_available():
            status = super().payment_status(org_id)
            status["credentials_present"] = bool(self._key_id and self._key_secret)
            status["webhook_secret_present"] = bool(self._webhook_secret)
            return status
        return {
            "org_id": org_id,
            "available": True,
            "provider": self.provider_name(),
            "status": "configured",
            "message": None,
            "subscription": None,
            "invoices": [],
            "checkout_enabled": True,
            "webhooks_configured": True,
            "credentials_present": True,
            "webhook_secret_present": True,
        }

    def create_checkout_session(
        self, org_id: str, *, plan: str | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        if not self.is_available():
            result = super().create_checkout_session(org_id, plan=plan, **kwargs)
            result["credentials_present"] = bool(self._key_id and self._key_secret)
            result["webhook_secret_present"] = bool(self._webhook_secret)
            return result
        try:
            amount_paise = int(kwargs.get("amount_paise") or 0)
        except (TypeError, ValueError):
            amount_paise = 0
        currency = str(kwargs.get("currency") or "INR").strip().upper() or "INR"
        if amount_paise < 1:
            return {
                "ok": False,
                "org_id": org_id,
                "provider": self.provider_name(),
                "message": "Unable to calculate.",
            }
        receipt = str(kwargs.get("receipt") or "")[:40]
        notes_in = kwargs.get("notes") or {}
        notes = {
            str(key): str(value)
            for key, value in dict(notes_in).items()
            if value is not None
        }
        client = self._client()
        if client is None:
            return {
                "ok": False,
                "org_id": org_id,
                "provider": self.provider_name(),
                "message": BILLING_PROVIDER_UNAVAILABLE,
            }
        body: dict[str, Any] = {
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt or f"dsp_{org_id}"[:40],
            "notes": notes,
        }
        try:
            created = client.post_json("/v1/orders", body)
        except RazorpayRequestError:
            return {
                "ok": False,
                "org_id": org_id,
                "provider": self.provider_name(),
                "message": BILLING_PROVIDER_UNAVAILABLE,
            }
        order_id = str(created.get("id") or "").strip()
        if not order_id:
            return {
                "ok": False,
                "org_id": org_id,
                "provider": self.provider_name(),
                "message": "Data unavailable.",
            }
        try:
            remote_amount = int(created.get("amount") or amount_paise)
        except (TypeError, ValueError):
            remote_amount = amount_paise
        return {
            "ok": True,
            "org_id": org_id,
            "provider": self.provider_name(),
            "key_id": self._key_id,
            "order_id": order_id,
            "amount": remote_amount,
            "currency": str(created.get("currency") or currency),
            "plan": plan,
        }

    def verify_webhook(self, payload: bytes, *, signature: str | None = None) -> dict[str, Any]:
        if not self._webhook_secret:
            return {
                "ok": False,
                "provider": self.provider_name(),
                "verified": False,
                "message": BILLING_PROVIDER_UNAVAILABLE,
            }
        expected = webhook_signature(payload, self._webhook_secret)
        verified = signatures_match(expected, signature)
        return {
            "ok": verified,
            "provider": self.provider_name(),
            "verified": verified,
            "message": None if verified else "Invalid webhook signature.",
        }

    def verify_checkout_signature(
        self, *, order_id: str, payment_id: str, signature: str
    ) -> dict[str, Any]:
        if not self._key_secret or not order_id or not payment_id:
            return {
                "ok": False,
                "provider": self.provider_name(),
                "verified": False,
                "message": BILLING_PROVIDER_UNAVAILABLE,
            }
        expected = checkout_signature(order_id, payment_id, self._key_secret)
        verified = signatures_match(expected, signature)
        return {
            "ok": verified,
            "provider": self.provider_name(),
            "verified": verified,
            "message": None if verified else "Invalid payment signature.",
        }

    def fetch_payment(self, payment_id: str) -> dict[str, Any]:
        client = self._client()
        pid = (payment_id or "").strip()
        if client is None or not pid:
            return {"ok": False, "available": False, "message": "Data unavailable."}
        try:
            entity = client.get_json(f"/v1/payments/{pid}")
        except RazorpayRequestError:
            return {"ok": False, "available": False, "message": "Data unavailable."}
        return {"ok": True, "available": True, "payment": entity}


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
