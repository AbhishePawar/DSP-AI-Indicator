"""Valuation Engine public API.

The Valuation Engine analyzes a :class:`~fundamental.models.FinancialSnapshot`
(and optional :class:`~valuation.models.MarketSnapshot`) and returns a
deterministic :class:`~valuation.models.ValuationAssessment`.

:class:`~contracts.MarginOfSafety` is a shared-kernel type calculated
once during aggregation and propagated via ``assessment.summary``.
"""

from contracts.domain.margin_of_safety import MarginOfSafety
from valuation.assumptions import ValuationAssumptions
from valuation.engine import ValuationEngine
from valuation.enums import ValuationConfidence, ValuationMethod
from valuation.exceptions import ValuationError
from valuation.models import (
    IntrinsicValueEstimate,
    MarketSnapshot,
    ValuationAssessment,
    ValuationEvidence,
    ValuationRange,
)

__all__ = [
    "IntrinsicValueEstimate",
    "MarginOfSafety",
    "MarketSnapshot",
    "ValuationAssessment",
    "ValuationAssumptions",
    "ValuationConfidence",
    "ValuationEngine",
    "ValuationError",
    "ValuationEvidence",
    "ValuationMethod",
    "ValuationRange",
]

__version__ = "0.1.1"
