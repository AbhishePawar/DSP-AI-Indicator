"""Billing abstraction — adapters only. No fake checkout or payment simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from enterprise.models import UNAVAILABLE_MESSAGES

__all__ = [
    "BillingPort",
    "InvoiceSummary",
    "NullBillingAdapter",
    "SubscriptionSummary",
]


@dataclass(frozen=True, slots=True)
class InvoiceSummary:
    invoice_id: str
    org_id: str
    status: str
    amount_cents: int | None
    currency: str | None
    issued_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "invoice_id": self.invoice_id,
            "org_id": self.org_id,
            "status": self.status,
            "amount_cents": self.amount_cents,
            "currency": self.currency,
            "issued_at": self.issued_at,
        }


@dataclass(frozen=True, slots=True)
class SubscriptionSummary:
    org_id: str
    status: str
    provider: str
    plan: str | None
    current_period_end: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "org_id": self.org_id,
            "status": self.status,
            "provider": self.provider,
            "plan": self.plan,
            "current_period_end": self.current_period_end,
        }


@runtime_checkable
class BillingPort(Protocol):
    """Port for billing providers. Implementations must not fabricate payments."""

    def provider_name(self) -> str: ...

    def is_available(self) -> bool: ...

    def get_subscription(self, org_id: str) -> SubscriptionSummary | None: ...

    def list_invoices(self, org_id: str) -> list[InvoiceSummary]: ...

    def payment_status(self, org_id: str) -> dict[str, Any]: ...


class NullBillingAdapter:
    """Default adapter — honest unavailable. No checkout, no simulated charges."""

    def provider_name(self) -> str:
        return "null"

    def is_available(self) -> bool:
        return False

    def get_subscription(self, org_id: str) -> SubscriptionSummary | None:
        return None

    def list_invoices(self, org_id: str) -> list[InvoiceSummary]:
        return []

    def payment_status(self, org_id: str) -> dict[str, Any]:
        return {
            "org_id": org_id,
            "available": False,
            "provider": self.provider_name(),
            "status": "unavailable",
            "message": UNAVAILABLE_MESSAGES["billing"],
            "subscription": None,
            "invoices": [],
        }
