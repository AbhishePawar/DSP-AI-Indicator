"""portfolio_analytics enumerations."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "AllocationDimension",
    "AnalyticsStatus",
    "RebalancingAction",
    "TaxTerm",
]


class AnalyticsStatus(StrEnum):
    """Overall computability status of an analytics result."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class AllocationDimension(StrEnum):
    """Dimension an allocation breakdown is grouped by."""

    SECTOR = "sector"
    COUNTRY = "country"


class RebalancingAction(StrEnum):
    """Suggested direction of a rebalancing delta — analysis only, never an order."""

    INCREASE = "increase"
    DECREASE = "decrease"
    HOLD = "hold"


class TaxTerm(StrEnum):
    """Holding-period tax classification."""

    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
