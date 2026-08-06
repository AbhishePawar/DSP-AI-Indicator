"""portfolio_intelligence_engine enumerations."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "AllocationKind",
    "DriftDirection",
    "IntelligenceStatus",
    "RecommendationAction",
    "ValuationClass",
]


class IntelligenceStatus(StrEnum):
    """Overall computability status of a combination result."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class ValuationClass(StrEnum):
    """Valuation classification derived from a caller-supplied margin of safety."""

    UNDERVALUED = "undervalued"
    FAIRLY_VALUED = "fairly_valued"
    OVERVALUED = "overvalued"
    UNAVAILABLE = "unavailable"


class RecommendationAction(StrEnum):
    """Rule-based portfolio action label — analysis only, never an order."""

    INCREASE = "increase"
    REDUCE = "reduce"
    HOLD = "hold"
    REVIEW = "review"
    WATCH = "watch"


class DriftDirection(StrEnum):
    """Direction of a sector/style/cap-bucket deviation from an even baseline."""

    OVERWEIGHT = "overweight"
    UNDERWEIGHT = "underweight"
    MISSING = "missing"
    IN_LINE = "in_line"


class AllocationKind(StrEnum):
    """Which allocation dimension a concentration flag refers to."""

    POSITION = "position"
    SECTOR = "sector"
    INDUSTRY = "industry"
    STYLE = "style"
    COUNTRY = "country"
