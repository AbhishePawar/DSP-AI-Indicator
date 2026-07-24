"""Package-local provider ports — Protocol interfaces only (E2.2).

Adapters live outside ``quantitative_risk``. Domain never imports vendor SDKs.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable

from core.exceptions import ValidationError

__all__ = [
    "BenchmarkDataPort",
    "HistoricalReturnsPort",
    "MarketDataPort",
    "ReturnPoint",
    "WeightPoint",
]


def _require_decimal(value: Decimal, *, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal):
        msg = f"{field} must be decimal.Decimal, never float"
        raise ValidationError(msg)
    if not value.is_finite():
        msg = f"{field} must be a finite Decimal"
        raise ValidationError(msg)
    return value


@dataclass(frozen=True, slots=True)
class WeightPoint:
    """Declared portfolio weight slice — Decimal only; never embeds Portfolio."""

    instrument_id: str
    weight: Decimal
    sector: str | None = None
    label: str | None = None

    def __post_init__(self) -> None:
        instrument_id = self.instrument_id.strip().lower()
        if not instrument_id or any(ch.isspace() for ch in instrument_id):
            msg = "instrument_id must be a non-empty id without whitespace"
            raise ValidationError(msg)
        weight = _require_decimal(self.weight, field="weight")
        sector = None if self.sector is None else self.sector.strip() or None
        label = None if self.label is None else self.label.strip() or None
        object.__setattr__(self, "instrument_id", instrument_id)
        object.__setattr__(self, "weight", weight)
        object.__setattr__(self, "sector", sector)
        object.__setattr__(self, "label", label)


@dataclass(frozen=True, slots=True)
class ReturnPoint:
    """Single period return observation — Decimal only."""

    timestamp: str
    value: Decimal

    def __post_init__(self) -> None:
        timestamp = self.timestamp.strip()
        if not timestamp:
            msg = "timestamp must not be empty"
            raise ValidationError(msg)
        value = _require_decimal(self.value, field="value")
        object.__setattr__(self, "timestamp", timestamp)
        object.__setattr__(self, "value", value)


@runtime_checkable
class MarketDataPort(Protocol):
    """Abstract market / declared-structure access for quantitative metrics."""

    def get_portfolio_weights(
        self,
        portfolio_id: str,
        *,
        as_of: str,
        snapshot_id: str | None = None,
    ) -> tuple[WeightPoint, ...] | None:
        """Return declared weights for concentration / exposure, or None if missing."""
        ...


@runtime_checkable
class HistoricalReturnsPort(Protocol):
    """Abstract historical return series access."""

    def get_returns(
        self,
        series_id: str,
        *,
        window_id: str,
    ) -> tuple[ReturnPoint, ...] | None:
        """Return ordered period returns, or None if missing."""
        ...


@runtime_checkable
class BenchmarkDataPort(Protocol):
    """Abstract benchmark series access."""

    def get_returns(
        self,
        benchmark_id: str,
        *,
        window_id: str,
    ) -> tuple[ReturnPoint, ...] | None:
        """Return ordered benchmark period returns, or None if missing."""
        ...
