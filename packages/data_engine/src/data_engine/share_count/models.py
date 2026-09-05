"""Authenticated current shares-outstanding models.

CURRENT SHARES OUTSTANDING is the point-in-time share COUNT used by
valuation to convert company-level intrinsic value into per-share
intrinsic value.

This is not weighted-average EPS shares, equity/paid-up capital, market
capitalization, shareholding percentage, F&O open interest, volume, or
an estimate. ``None`` means unavailable and is never coerced to zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from data_engine.exceptions import InvalidProviderDataError

__all__ = [
    "ShareCountBasis",
    "ShareCountField",
    "ShareCountProvenance",
    "ShareCountSnapshot",
    "ShareCountUnit",
    "utc_now",
]

_SECRET_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "auth_header",
    "bearer",
    "password",
    "passwd",
    "secret",
    "token",
    "jwt",
    "private_key",
    "access_key",
    "client_secret",
    "credential",
    "cookie",
)

_CURRENCY_OR_PERCENT_MARKERS = frozenset("%$€£¥₹")


class ShareCountBasis(StrEnum):
    """Semantic basis of a share-count observation.

    Only ``CURRENT_OUTSTANDING`` may populate valuation ``shares_outstanding``.
    """

    CURRENT_OUTSTANDING = "current_outstanding"
    WEIGHTED_AVERAGE_BASIC = "weighted_average_shares_basic"
    WEIGHTED_AVERAGE_DILUTED = "weighted_average_shares_diluted"


class ShareCountUnit(StrEnum):
    """Unit of a share-count observation — a number of shares, never money."""

    SHARES = "shares"


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _safe_metadata(metadata: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in dict(metadata or {}).items():
        key_l = str(key).lower()
        if any(frag in key_l for frag in _SECRET_KEY_FRAGMENTS):
            continue
        out[str(key)] = str(value)
    return out


@dataclass(frozen=True, slots=True)
class ShareCountField:
    """Single numeric share-count field — absent means unavailable."""

    value: Decimal | None
    available: bool

    @classmethod
    def of(cls, value: Decimal | float | int | str | None) -> ShareCountField:
        if value is None:
            return cls(value=None, available=False)
        if isinstance(value, bool):
            raise InvalidProviderDataError("share count must be numeric")
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return cls(value=None, available=False)
            if any(marker in stripped for marker in _CURRENCY_OR_PERCENT_MARKERS):
                raise InvalidProviderDataError(
                    "share count must be a number of shares, not currency/percentage"
                )
            raw = stripped
        else:
            raw = value
        try:
            dec = raw if isinstance(raw, Decimal) else Decimal(str(raw))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise InvalidProviderDataError("share count must be numeric") from exc
        if not dec.is_finite():
            raise InvalidProviderDataError("share count must be finite")
        return cls(value=dec, available=True)

    @classmethod
    def missing(cls) -> ShareCountField:
        return cls(value=None, available=False)


@dataclass(frozen=True, slots=True)
class ShareCountProvenance:
    """Source metadata for current shares outstanding.

    Separate from quote provenance and statement provenance.
    """

    provider_id: str
    provider_name: str
    source_type: str
    retrieved_at: datetime
    as_of: datetime | None = None
    request_id: str | None = None
    cache_hit: bool = False
    auth_mode: str = "api_key"
    endpoint: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _safe_metadata(self.metadata))

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
            "endpoint": self.endpoint,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ShareCountSnapshot:
    """Point-in-time authenticated share COUNT for one identified instrument."""

    symbol: str
    shares: ShareCountField
    basis: ShareCountBasis
    unit: ShareCountUnit
    provenance: ShareCountProvenance
    exchange: str | None = None
    isin: str | None = None
    as_of: datetime | None = None

    def shares_value(self) -> float | None:
        """Return the share count as float, or ``None`` when unavailable.

        Never coerces ``None`` to zero.
        """
        if not self.shares.available or self.shares.value is None:
            return None
        return float(self.shares.value)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "isin": self.isin,
            "shares": self.shares_value(),
            "basis": str(self.basis),
            "unit": str(self.unit),
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "authenticated": True,
            "provenance": self.provenance.to_dict(),
        }
