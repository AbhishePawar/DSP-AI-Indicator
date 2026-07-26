"""Earnings Quality & Predictability public API (FEATURE-004 Phase 1)."""

from __future__ import annotations

from earnings_quality.engine import EarningsQualityEngine
from earnings_quality.exceptions import (
    EarningsQualityError,
    EarningsQualityValidationError,
)
from earnings_quality.metadata import (
    EARNINGS_QUALITY_VERSION,
    FRAMEWORK_VERSION,
    EarningsQualityMetadata,
)
from earnings_quality.models import (
    EarningsQualityAnalysis,
    EarningsQualityComponentScore,
    EarningsQualityConfidence,
    EarningsQualityEvidence,
    EarningsQualityExplainability,
    EarningsQualityScore,
    EarningsQualityValidationSummary,
)
from earnings_quality.scoring import (
    DEFAULT_EARNINGS_WEIGHTS,
    EarningsQualityDimension,
    EarningsQualityRating,
    EarningsQualityWeights,
    earnings_rating_from_score,
    validate_weights,
)

__all__ = [
    "DEFAULT_EARNINGS_WEIGHTS",
    "EARNINGS_QUALITY_VERSION",
    "FRAMEWORK_VERSION",
    "EarningsQualityAnalysis",
    "EarningsQualityComponentScore",
    "EarningsQualityConfidence",
    "EarningsQualityDimension",
    "EarningsQualityEngine",
    "EarningsQualityError",
    "EarningsQualityEvidence",
    "EarningsQualityExplainability",
    "EarningsQualityMetadata",
    "EarningsQualityRating",
    "EarningsQualityScore",
    "EarningsQualityValidationError",
    "EarningsQualityValidationSummary",
    "EarningsQualityWeights",
    "earnings_rating_from_score",
    "validate_weights",
]

__version__ = "0.1.0"
