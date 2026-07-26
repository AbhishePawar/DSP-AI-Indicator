"""Growth Quality & Capital Reinvestment public API (FEATURE-005 Phase 1)."""

from __future__ import annotations

from growth_quality.engine import GrowthQualityEngine
from growth_quality.exceptions import GrowthQualityError, GrowthQualityValidationError
from growth_quality.metadata import (
    GROWTH_QUALITY_VERSION,
    FRAMEWORK_VERSION,
    GrowthQualityMetadata,
)
from growth_quality.models import (
    GrowthQualityAnalysis,
    GrowthQualityComponentScore,
    GrowthQualityConfidence,
    GrowthQualityEvidence,
    GrowthQualityExplainability,
    GrowthQualityScore,
    GrowthQualityValidationSummary,
)
from growth_quality.scoring import (
    DEFAULT_GROWTH_WEIGHTS,
    GrowthQualityDimension,
    GrowthQualityRating,
    GrowthQualityWeights,
    growth_rating_from_score,
    validate_weights,
)

__all__ = [
    "DEFAULT_GROWTH_WEIGHTS",
    "FRAMEWORK_VERSION",
    "GROWTH_QUALITY_VERSION",
    "GrowthQualityAnalysis",
    "GrowthQualityComponentScore",
    "GrowthQualityConfidence",
    "GrowthQualityDimension",
    "GrowthQualityEngine",
    "GrowthQualityError",
    "GrowthQualityEvidence",
    "GrowthQualityExplainability",
    "GrowthQualityMetadata",
    "GrowthQualityRating",
    "GrowthQualityScore",
    "GrowthQualityValidationError",
    "GrowthQualityValidationSummary",
    "GrowthQualityWeights",
    "growth_rating_from_score",
    "validate_weights",
]

__version__ = "0.1.0"
