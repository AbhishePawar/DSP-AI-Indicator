"""Business Quality Aggregator public API (FEATURE-006 Phase 1).

Cross-domain composition of Economic Moat, Management Quality, Financial Strength,
Earnings Quality, and Growth Quality. Distinct from F3.7
``business_quality.BusinessQualityAggregator``.
"""

from __future__ import annotations

from business_quality_aggregator.engine import BusinessQualityAggregatorEngine
from business_quality_aggregator.exceptions import (
    BusinessQualityAggregatorError,
    BusinessQualityAggregatorValidationError,
)
from business_quality_aggregator.metadata import (
    AGGREGATOR_VERSION,
    FRAMEWORK_VERSION,
    BusinessQualityAggregatorMetadata,
)
from business_quality_aggregator.models import (
    AggregatorComponentResult,
    BusinessQualityAggregation,
    BusinessQualityAggregatorConfidence,
    BusinessQualityAggregatorEvidence,
    BusinessQualityAggregatorExplainability,
    BusinessQualityAggregatorScore,
    BusinessQualityAggregatorValidationSummary,
    ConflictAdjustment,
)
from business_quality_aggregator.scoring import (
    DEFAULT_AGGREGATOR_WEIGHTS,
    AggregatorComponent,
    BusinessQualityAggregatorRating,
    BusinessQualityAggregatorWeights,
    aggregator_rating_from_score,
    validate_weights,
)

__all__ = [
    "AGGREGATOR_VERSION",
    "DEFAULT_AGGREGATOR_WEIGHTS",
    "FRAMEWORK_VERSION",
    "AggregatorComponent",
    "AggregatorComponentResult",
    "BusinessQualityAggregation",
    "BusinessQualityAggregatorConfidence",
    "BusinessQualityAggregatorEngine",
    "BusinessQualityAggregatorError",
    "BusinessQualityAggregatorEvidence",
    "BusinessQualityAggregatorExplainability",
    "BusinessQualityAggregatorMetadata",
    "BusinessQualityAggregatorRating",
    "BusinessQualityAggregatorScore",
    "BusinessQualityAggregatorValidationError",
    "BusinessQualityAggregatorValidationSummary",
    "BusinessQualityAggregatorWeights",
    "ConflictAdjustment",
    "aggregator_rating_from_score",
    "validate_weights",
]

__version__ = "0.1.0"
