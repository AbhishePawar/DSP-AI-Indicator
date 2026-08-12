"""Authenticated market quote models (EPIC-D001) — RS-002 field set + provenance."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

__all__ = [
    "AuthenticatedMarketQuote",
    "MarketQuoteProvenance",
    "QuoteField",
    "utc_now",
]


@dataclass(frozen=True, slots=True)
class QuoteField:
    """Single numeric quote field — absent means unavailable, never invented."""

    value: Decimal | None
    available: bool

    @classmethod
    def of(cls, value: Decimal | float | int | str | None) -> QuoteField:
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
    def missing(cls) -> QuoteField:
        return cls(value=None, available=False)


@dataclass(frozen=True, slots=True)
class MarketQuoteProvenance:
    """Source metadata for CV-001 / RS-002 / RS-010."""

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
class AuthenticatedMarketQuote:
    """RS-002 market snapshot from an authenticated provider only."""

    symbol: str
    exchange: str | None
    currency: str | None
    current_price: QuoteField
    open: QuoteField
    high: QuoteField
    low: QuoteField
    previous_close: QuoteField
    week_52_high: QuoteField
    week_52_low: QuoteField
    volume: QuoteField
    average_volume: QuoteField
    market_cap: QuoteField
    enterprise_value: QuoteField
    shares_outstanding: QuoteField
    dividend_yield: QuoteField
    beta: QuoteField
    provenance: MarketQuoteProvenance

    def has_any_price(self) -> bool:
        return self.current_price.available or self.previous_close.available

    def to_public_dict(self) -> dict[str, Any]:
        def _f(q: QuoteField) -> float | None:
            if not q.available or q.value is None:
                return None
            return float(q.value)

        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "currency": self.currency,
            "authenticated": True,
            "fields": {
                "current_price": _f(self.current_price),
                "open": _f(self.open),
                "high": _f(self.high),
                "low": _f(self.low),
                "previous_close": _f(self.previous_close),
                "week_52_high": _f(self.week_52_high),
                "week_52_low": _f(self.week_52_low),
                "volume": _f(self.volume),
                "average_volume": _f(self.average_volume),
                "market_cap": _f(self.market_cap),
                "enterprise_value": _f(self.enterprise_value),
                "shares_outstanding": _f(self.shares_outstanding),
                "dividend_yield": _f(self.dividend_yield),
                "beta": _f(self.beta),
            },
            "provenance": self.provenance.to_dict(),
        }


def utc_now() -> datetime:
    return datetime.now(tz=UTC)
