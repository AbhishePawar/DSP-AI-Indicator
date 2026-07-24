"""Intermediate, strictly-typed records used between Normalize and Validate.

A "normalized record" sits between a raw model and a ``contracts``
object: its fields have already been coerced to their target Python
types (unlike a raw model, where every field is ``Any``), but it has
not yet passed semantic validation (duplicate/sort/OHLC/volume checks)
and is not a ``contracts`` type. It exists purely as the value handed
from the Normalize stage to the Validate stage inside a
:class:`data_engine.normalization.pipeline.TransformationPipeline`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from contracts.enums import EconomicFrequency, StatementPeriodType

__all__ = ["NormalizedBar", "NormalizedObservation", "NormalizedStatement"]



@dataclass(frozen=True, slots=True)
class NormalizedBar:
    """A single price bar after raw-value coercion, before validation.

    Attributes:
        timestamp: Timezone-aware bar timestamp.
        open: Coerced opening price.
        high: Coerced high price.
        low: Coerced low price.
        close: Coerced closing price.
        volume: Coerced traded volume (``0.0`` if the provider omitted
            it).
        adjusted_close: Coerced adjusted close, if the provider
            reported one.
    """

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjusted_close: float | None = None


@dataclass(frozen=True, slots=True)
class NormalizedStatement:
    """One financial statement after raw-value coercion, before contracts construction.

    Attributes:
        period_end: Coerced reporting-period end date.
        period_type: Canonical statement period type.
        fiscal_year: Coerced fiscal year.
        currency: Uppercased ISO-4217 currency code.
        line_items: Canonical field name → coerced optional float for
            every known ``FundamentalStatement`` monetary/EPS field.
        extra_line_items: Additional ``(label, value)`` pairs (ratios,
            shares outstanding, market cap, enterprise value, etc.).
    """

    period_end: date
    period_type: StatementPeriodType
    fiscal_year: int
    currency: str
    line_items: dict[str, float | None]
    extra_line_items: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True, slots=True)
class NormalizedObservation:
    """One economic observation after coercion, before contracts construction.

    Attributes:
        observation_date: Coerced calendar date.
        value: Coerced finite numeric value.
    """

    observation_date: date
    value: float
