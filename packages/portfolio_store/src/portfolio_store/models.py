"""Portfolio persistence domain models (RC1 Milestone 3).

Holdings deliberately mirror ``portfolio_analytics.PositionInput`` /
``PortfolioAnalyticsHolding`` field-for-field — this package never invents a
parallel holding shape. Transactions are an append-only ledger only; no
reconciliation into holdings happens here (see README "what this does not
do").
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

__all__ = [
    "PORTFOLIO_STORE_SCHEMA_VERSION",
    "PORTFOLIO_STORE_SERVICE_VERSION",
    "TRANSACTION_TYPES",
    "Holding",
    "Portfolio",
    "Transaction",
    "WatchlistItem",
    "freeze_mapping",
    "utc_now",
]

PORTFOLIO_STORE_SCHEMA_VERSION = "1.0.0"
PORTFOLIO_STORE_SERVICE_VERSION = "1.0.0"

#: Supported transaction types — append-only ledger entries.
TRANSACTION_TYPES = (
    "buy",
    "sell",
    "dividend",
    "bonus",
    "split",
    "rights",
    "fee",
    "tax",
    "cash_deposit",
    "cash_withdrawal",
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if value is None:
        return MappingProxyType({})

    def _freeze(obj: Any) -> Any:
        if isinstance(obj, Mapping):
            return MappingProxyType({str(k): _freeze(v) for k, v in obj.items()})
        if isinstance(obj, (list, tuple)):
            return tuple(_freeze(v) for v in obj)
        return obj

    return _freeze(value)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class Portfolio:
    """A user-owned portfolio. ``org_id`` is reserved, unused today.

    Organization ownership can be layered on later (e.g. authorizing by
    ``org_id`` membership instead of/alongside ``user_id``) without a schema
    change — the field already exists and is simply ``None`` until then.
    """

    portfolio_id: str
    user_id: str
    name: str
    is_default: bool
    created_at: str
    updated_at: str
    org_id: str | None = None
    benchmark_symbol: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "user_id": self.user_id,
            "org_id": self.org_id,
            "name": self.name,
            "is_default": self.is_default,
            "benchmark_symbol": self.benchmark_symbol,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class Holding:
    """One position within a portfolio — shape matches ``PositionInput``."""

    holding_id: str
    portfolio_id: str
    symbol: str
    weight: float
    created_at: str
    updated_at: str
    units: float | None = None
    cost_basis_per_unit: float | None = None
    purchase_date: str | None = None
    sector: str | None = None
    country: str | None = None
    exchange: str | None = None
    value_score: float | None = None
    quality_score: float | None = None
    momentum_score: float | None = None
    size_score: float | None = None
    volatility_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "holding_id": self.holding_id,
            "portfolio_id": self.portfolio_id,
            "symbol": self.symbol,
            "weight": self.weight,
            "units": self.units,
            "cost_basis_per_unit": self.cost_basis_per_unit,
            "purchase_date": self.purchase_date,
            "sector": self.sector,
            "country": self.country,
            "exchange": self.exchange,
            "value_score": self.value_score,
            "quality_score": self.quality_score,
            "momentum_score": self.momentum_score,
            "size_score": self.size_score,
            "volatility_score": self.volatility_score,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True, slots=True)
class Transaction:
    """One append-only ledger entry — never updated or deleted in place."""

    transaction_id: str
    portfolio_id: str
    transaction_type: str
    transaction_date: str
    created_at: str
    symbol: str | None = None
    quantity: float | None = None
    price: float | None = None
    amount: float | None = None
    currency: str = "USD"
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "portfolio_id": self.portfolio_id,
            "transaction_type": self.transaction_type,
            "transaction_date": self.transaction_date,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "price": self.price,
            "amount": self.amount,
            "currency": self.currency,
            "notes": self.notes,
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class WatchlistItem:
    """One watched symbol scoped to a portfolio."""

    item_id: str
    portfolio_id: str
    symbol: str
    added_at: str
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "portfolio_id": self.portfolio_id,
            "symbol": self.symbol,
            "label": self.label,
            "added_at": self.added_at,
        }
