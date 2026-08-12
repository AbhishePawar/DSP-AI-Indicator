"""Authenticated corporate action models (EPIC-D003).

Retrieval and validation only — no adjusted prices, valuation, or scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

__all__ = [
    "ACTION_TYPES",
    "AuthenticatedCorporateAction",
    "AuthenticatedCorporateActions",
    "CorporateActionCompanyIdentity",
    "CorporateActionField",
    "CorporateActionProvenance",
    "utc_now",
]

ACTION_TYPES = frozenset(
    {
        "stock_split",
        "bonus_issue",
        "dividend",
        "rights_issue",
        "buyback",
        "merger",
        "demerger",
        "symbol_change",
        "share_capital_change",
    }
)


@dataclass(frozen=True, slots=True)
class CorporateActionField:
    """Optional numeric field — absent means unavailable, never invented."""

    value: Decimal | None
    available: bool

    @classmethod
    def of(cls, value: Decimal | float | int | str | None) -> CorporateActionField:
        if value is None:
            return cls(value=None, available=False)
        if isinstance(value, str) and not value.strip():
            return cls(value=None, available=False)
        try:
            dec = value if isinstance(value, Decimal) else Decimal(str(value))
        except Exception:
            return cls(value=None, available=False)
        return cls(value=dec, available=True)

    @classmethod
    def missing(cls) -> CorporateActionField:
        return cls(value=None, available=False)


@dataclass(frozen=True, slots=True)
class CorporateActionCompanyIdentity:
    """Resolved company identifier for corporate actions."""

    symbol: str
    exchange: str | None = None
    company_name: str | None = None
    isin: str | None = None
    provider_company_id: str | None = None
    currency: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "company_name": self.company_name,
            "isin": self.isin,
            "provider_company_id": self.provider_company_id,
            "currency": self.currency,
        }


@dataclass(frozen=True, slots=True)
class CorporateActionProvenance:
    """Source metadata for CV-001 / RS-010."""

    provider_id: str
    provider_name: str
    source_type: str
    retrieved_at: datetime
    as_of: datetime | None = None
    request_id: str | None = None
    cache_hit: bool = False
    auth_mode: str = "api_key"
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "source_type": self.source_type,
            "retrieved_at": self.retrieved_at.isoformat(),
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "request_id": self.request_id,
            "cache_hit": self.cache_hit,
            "auth_mode": self.auth_mode,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class AuthenticatedCorporateAction:
    """One authenticated corporate action event — as-reported fields only."""

    action_id: str
    action_type: str
    symbol: str
    description: str | None
    effective_date: date | None
    ex_date: date | None
    record_date: date | None
    payment_date: date | None
    announcement_date: date | None
    currency: str | None
    # Optional as-reported numerics (never calculated / never used to adjust prices here)
    ratio_from: CorporateActionField
    ratio_to: CorporateActionField
    amount: CorporateActionField
    shares: CorporateActionField
    old_symbol: str | None = None
    new_symbol: str | None = None
    status: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        def _f(q: CorporateActionField) -> float | None:
            if not q.available or q.value is None:
                return None
            return float(q.value)

        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "symbol": self.symbol,
            "description": self.description,
            "effective_date": self.effective_date.isoformat()
            if self.effective_date
            else None,
            "ex_date": self.ex_date.isoformat() if self.ex_date else None,
            "record_date": self.record_date.isoformat() if self.record_date else None,
            "payment_date": self.payment_date.isoformat()
            if self.payment_date
            else None,
            "announcement_date": self.announcement_date.isoformat()
            if self.announcement_date
            else None,
            "currency": self.currency,
            "ratio_from": _f(self.ratio_from),
            "ratio_to": _f(self.ratio_to),
            "amount": _f(self.amount),
            "shares": _f(self.shares),
            "old_symbol": self.old_symbol,
            "new_symbol": self.new_symbol,
            "status": self.status,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class AuthenticatedCorporateActions:
    """Authenticated historical corporate actions bundle for one company."""

    identity: CorporateActionCompanyIdentity
    events: tuple[AuthenticatedCorporateAction, ...]
    provenance: CorporateActionProvenance

    def has_any_event(self) -> bool:
        return len(self.events) > 0

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "authenticated": True,
            "identity": self.identity.to_dict(),
            "events": [e.to_public_dict() for e in self.events],
            "provenance": self.provenance.to_dict(),
        }


def utc_now() -> datetime:
    return datetime.now(tz=UTC)
