"""Authenticated historical time-series models (EPIC-D004).

Retrieval and validation only — no indicators, TA, valuation, or scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

__all__ = [
    "BAR_FREQUENCIES",
    "AuthenticatedHistoricalBundle",
    "AuthenticatedOhlcvBar",
    "AuthenticatedPoint",
    "AuthenticatedSnapshot",
    "HistoricalCompanyIdentity",
    "HistoricalField",
    "HistoricalProvenance",
    "SERIES_KINDS",
    "utc_now",
]

BAR_FREQUENCIES = frozenset({"daily", "weekly", "monthly"})
SERIES_KINDS = frozenset(
    {
        "ohlcv",
        "market_cap",
        "volume",
        "enterprise_value",
        "fundamentals",
        "ratios",
    }
)


@dataclass(frozen=True, slots=True)
class HistoricalField:
    """Optional numeric field — absent means unavailable, never invented."""

    value: Decimal | None
    available: bool

    @classmethod
    def of(cls, value: Decimal | float | int | str | None) -> HistoricalField:
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
    def missing(cls) -> HistoricalField:
        return cls(value=None, available=False)


@dataclass(frozen=True, slots=True)
class HistoricalCompanyIdentity:
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
class HistoricalProvenance:
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
class AuthenticatedOhlcvBar:
    """One authenticated OHLCV bar — as-reported, not adjusted or calculated."""

    bar_date: date
    open: HistoricalField
    high: HistoricalField
    low: HistoricalField
    close: HistoricalField
    volume: HistoricalField
    frequency: str = "daily"

    def to_public_dict(self) -> dict[str, Any]:
        def _f(q: HistoricalField) -> float | None:
            if not q.available or q.value is None:
                return None
            return float(q.value)

        return {
            "date": self.bar_date.isoformat(),
            "frequency": self.frequency,
            "open": _f(self.open),
            "high": _f(self.high),
            "low": _f(self.low),
            "close": _f(self.close),
            "volume": _f(self.volume),
        }


@dataclass(frozen=True, slots=True)
class AuthenticatedPoint:
    """Single dated scalar series point (market cap, volume, EV, etc.)."""

    point_date: date
    value: HistoricalField
    series_kind: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "date": self.point_date.isoformat(),
            "series_kind": self.series_kind,
            "value": float(self.value.value)
            if self.value.available and self.value.value is not None
            else None,
        }


@dataclass(frozen=True, slots=True)
class AuthenticatedSnapshot:
    """Dated fundamentals or ratios snapshot — pass-through fields only."""

    as_of: date
    series_kind: str  # fundamentals | ratios
    fields: dict[str, HistoricalField]

    def to_public_dict(self) -> dict[str, Any]:
        out: dict[str, float | None] = {}
        for key, field in self.fields.items():
            out[key] = (
                float(field.value)
                if field.available and field.value is not None
                else None
            )
        return {
            "as_of": self.as_of.isoformat(),
            "series_kind": self.series_kind,
            "fields": out,
        }


@dataclass(frozen=True, slots=True)
class AuthenticatedHistoricalBundle:
    """Authenticated historical bundle for one company / series query."""

    identity: HistoricalCompanyIdentity
    series_kind: str
    frequency: str | None
    start_date: date | None
    end_date: date | None
    bars: tuple[AuthenticatedOhlcvBar, ...]
    points: tuple[AuthenticatedPoint, ...]
    snapshots: tuple[AuthenticatedSnapshot, ...]
    provenance: HistoricalProvenance
    currency: str | None = None

    def has_any_observation(self) -> bool:
        return bool(self.bars or self.points or self.snapshots)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "authenticated": True,
            "identity": self.identity.to_dict(),
            "series_kind": self.series_kind,
            "frequency": self.frequency,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "currency": self.currency or self.identity.currency,
            "bars": [b.to_public_dict() for b in self.bars],
            "points": [p.to_public_dict() for p in self.points],
            "snapshots": [s.to_public_dict() for s in self.snapshots],
            "provenance": self.provenance.to_dict(),
        }


def utc_now() -> datetime:
    return datetime.now(tz=UTC)
