"""Qualitative Comparison Engine (AIMF C2.5).

Compares DecisionPacks after peer eligibility. Explains differences —
does not score, rank, or declare winners.
"""

from __future__ import annotations

from comparison.engine import QualitativeComparisonEngine
from comparison.enums import ComparisonStatus
from comparison.exceptions import ComparisonError
from comparison.models import (
    ComparisonDimensionResult,
    ComparisonEvidenceSummary,
    ComparisonExplanation,
    ComparisonLimitation,
    ComparisonObservation,
    ComparisonReport,
    ComparisonRequest,
    ComparisonResult,
)
from comparison.universe_bridge import compare_universe_result

__all__ = [
    "ComparisonDimensionResult",
    "ComparisonError",
    "ComparisonEvidenceSummary",
    "ComparisonExplanation",
    "ComparisonLimitation",
    "ComparisonObservation",
    "ComparisonReport",
    "ComparisonRequest",
    "ComparisonResult",
    "ComparisonStatus",
    "QualitativeComparisonEngine",
    "compare_universe_result",
]

__version__ = "0.2.0"
