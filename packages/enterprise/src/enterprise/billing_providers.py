"""Production billing provider adapters (EPIC-016)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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

    def create_checkout_session(
        self, org_id: str, *, plan: str | None = None
    ) -> dict[str, Any]:
        _ = plan
        return {
            "ok": False,
            "org_id": org_id,
            "provider": self.provider_name(),
            "message": BILLING_PROVIDER_UNAVAILABLE,
        }

    def verify_webhook(
        self, payload: bytes, *, signature: str | None = None
    ) -> dict[str, Any]:
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

    def __init__(
        self, *, api_key: str | None = None, webhook_secret: str | None = None
    ) -> None:
        self._api_key = (
            api_key or os.environ.get("DSP_STRIPE_SECRET_KEY") or ""
        ).strip()
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
        plan_amounts: dict[str, int] | None = None,
        currency: str | None = None,
    ) -> None:
        self._key_id = (key_id or os.environ.get("DSP_RAZORPAY_KEY_ID") or "").strip()
        self._key_secret = (
            key_secret or os.environ.get("DSP_RAZORPAY_KEY_SECRET") or ""
        ).strip()
        self._webhook_secret = (
            webhook_secret or os.environ.get("DSP_RAZORPAY_WEBHOOK_SECRET") or ""
        ).strip()
        configured = os.environ.get("DSP_RAZORPAY_PLAN_AMOUNTS", "{}")
        try:
            env_amounts = json.loads(configured)
        except (TypeError, ValueError):
            env_amounts = {}
        self._plan_amounts = dict(plan_amounts or env_amounts)
        self._currency = (
            currency or os.environ.get("DSP_RAZORPAY_CURRENCY") or "INR"
        ).upper()

    def is_available(self) -> bool:
        return bool(
            self._key_id
            and self._key_secret
            and self._webhook_secret
            and self._plan_amounts
        )

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        body = json.dumps(payload or {}).encode("utf-8")
        token = base64.b64encode(f"{self._key_id}:{self._key_secret}".encode()).decode()
        request = Request(
            f"https://api.razorpay.com/v1/{path.lstrip('/')}",
            data=body if method != "GET" else None,
            headers={
                "Authorization": f"Basic {token}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        try:
            with urlopen(request, timeout=10) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise RuntimeError("Razorpay request failed") from exc

    def create_checkout_session(
        self, org_id: str, *, plan: str | None = None
    ) -> dict[str, Any]:
        plan_id = (plan or "").strip().lower()
        amount = self._plan_amounts.get(plan_id)
        if (
            not self.is_available()
            or not plan_id
            or not isinstance(amount, int)
            or amount <= 0
        ):
            return {
                "ok": False,
                "org_id": org_id,
                "provider": self.provider_name(),
                "message": BILLING_PROVIDER_UNAVAILABLE,
            }
        order = self._request(
            "POST",
            "orders",
            {
                "amount": amount,
                "currency": self._currency,
                "receipt": f"dsp_{org_id}_{plan_id}",
                "notes": {"org_id": org_id, "plan": plan_id},
            },
        )
        return {
            "ok": True,
            "org_id": org_id,
            "provider": self.provider_name(),
            "order_id": order["id"],
            "amount": amount,
            "currency": self._currency,
            "plan": plan_id,
            "status": order.get("status"),
        }

    def verify_webhook(
        self, payload: bytes, *, signature: str | None = None
    ) -> dict[str, Any]:
        if not self._webhook_secret or not signature:
            return {
                "ok": False,
                "provider": self.provider_name(),
                "verified": False,
                "message": BILLING_PROVIDER_UNAVAILABLE,
            }
        expected = hmac.new(
            self._webhook_secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        verified = hmac.compare_digest(expected, signature.strip())
        return {
            "ok": verified,
            "provider": self.provider_name(),
            "verified": verified,
            "event": json.loads(payload.decode("utf-8")) if verified else None,
        }

    def payment_status(self, org_id: str) -> dict[str, Any]:
        status = super().payment_status(org_id)
        status["credentials_present"] = bool(self._key_id and self._key_secret)
        status["webhook_secret_present"] = bool(self._webhook_secret)
        status["plan_catalog_configured"] = bool(self._plan_amounts)
        status["checkout_enabled"] = self.is_available()
        status["webhooks_configured"] = bool(self._webhook_secret)
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
    name = (
        (provider or os.environ.get("DSP_BILLING_PROVIDER") or "null").strip().lower()
    )
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
