"""Shared envelope models for the Data Connector Framework.

These are deliberately the *only* new dataclasses shared across all six
new domains (News, Filings, Ownership, Insider Trading, ESG,
Transcripts). Domain-specific event models (``NewsArticle``,
``Filing``, ``OwnershipStake``, ...) live in each domain's own
``models.py`` — this module never grows vendor- or domain-specific
fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

__all__ = [
    "ConnectorCompanyIdentity",
    "ConnectorField",
    "ConnectorProvenance",
    "ProviderHealth",
    "utc_now",
]


def utc_now() -> datetime:
    """Current UTC time — the single clock every connector provenance uses."""
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class ConnectorCompanyIdentity:
    """Resolved company identity, shared shape across every connector domain."""

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
class ConnectorProvenance:
    """Source metadata attached to every connector response.

    Mirrors ``CorporateActionProvenance`` / ``MarketQuoteProvenance`` —
    every authenticated payload in this platform carries who produced
    it, when, and how, so nothing downstream has to guess.
    """

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
class ProviderHealth:
    """Provider health for readiness probes — shared shape across domains."""

    provider_id: str
    healthy: bool
    authenticated: bool
    detail: str
    checked_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "healthy": self.healthy,
            "authenticated": self.authenticated,
            "detail": self.detail,
            "checked_at": self.checked_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ConnectorField:
    """Optional numeric field — absent means unavailable, never invented.

    Shared numeric-field envelope for domains with as-reported numerics
    (ownership percentages/shares, insider transaction amounts, ESG
    scores) — mirrors ``CorporateActionField`` / ``QuoteField``.
    """

    value: Decimal | None
    available: bool

    @classmethod
    def of(cls, value: Decimal | float | int | str | None) -> ConnectorField:
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
    def missing(cls) -> ConnectorField:
        return cls(value=None, available=False)

    def to_float(self) -> float | None:
        if not self.available or self.value is None:
            return None
        return float(self.value)
