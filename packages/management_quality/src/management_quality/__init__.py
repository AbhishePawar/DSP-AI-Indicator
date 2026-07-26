"""Management Quality Intelligence public API (FEATURE-002 Phase 1)."""

from __future__ import annotations

from management_quality.engine import ManagementEngine
from management_quality.exceptions import (
    ManagementQualityError,
    ManagementQualityValidationError,
)
from management_quality.metadata import (
    MANAGEMENT_QUALITY_VERSION,
    FRAMEWORK_VERSION,
    ManagementMetadata,
)
from management_quality.models import (
    ManagementAnalysis,
    ManagementComponentScore,
    ManagementConfidence,
    ManagementEvidence,
    ManagementExplainability,
    ManagementScore,
    ManagementValidationSummary,
)
from management_quality.scoring import (
    DEFAULT_MANAGEMENT_WEIGHTS,
    ManagementDimension,
    ManagementRating,
    ManagementWeights,
    management_rating_from_score,
    validate_weights,
)

__all__ = [
    "DEFAULT_MANAGEMENT_WEIGHTS",
    "FRAMEWORK_VERSION",
    "MANAGEMENT_QUALITY_VERSION",
    "ManagementAnalysis",
    "ManagementComponentScore",
    "ManagementConfidence",
    "ManagementDimension",
    "ManagementEngine",
    "ManagementEvidence",
    "ManagementExplainability",
    "ManagementMetadata",
    "ManagementQualityError",
    "ManagementQualityValidationError",
    "ManagementRating",
    "ManagementScore",
    "ManagementValidationSummary",
    "ManagementWeights",
    "management_rating_from_score",
    "validate_weights",
]

__version__ = "0.1.0"
