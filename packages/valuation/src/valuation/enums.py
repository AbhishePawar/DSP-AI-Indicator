"""Valuation Engine enumerations.

Engine-local vocabulary (not ``contracts``). Sprint 8.1 will map
assessments into committee context.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["ValuationConfidence", "ValuationMethod"]


class ValuationMethod(StrEnum):
    """Canonical identifiers for independent valuation methodologies."""

    DCF = "dcf"
    OWNER_EARNINGS = "owner_earnings"
    EARNINGS_MULTIPLE = "earnings_multiple"
    BOOK_VALUE = "book_value"
    RESIDUAL_INCOME = "residual_income"


class ValuationConfidence(StrEnum):
    """Confidence in the aggregated intrinsic-value assessment.

    Driven by how many independent methods produced usable estimates —
    not by market forecasting.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"
