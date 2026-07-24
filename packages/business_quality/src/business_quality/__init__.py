"""Canonical Business Quality Intelligence — public package surface.

Phase 3 / F3.1–F3.3: framework + Earnings Quality + Capital Allocation.
Consumes FinancialAnalysis only; no valuation or forecasting.
"""

from __future__ import annotations

from business_quality.capital_allocation_engine import (
    CAPITAL_ALLOCATION_VERSION,
    CapitalAllocationEngine,
)
from business_quality.capital_allocation_explainability import (
    CAPITAL_ALLOCATION_DISCLAIMER,
)
from business_quality.capital_allocation_models import (
    CapitalAllocationAnalysis,
    CapitalAllocationFlag,
)
from business_quality.capital_allocation_validation import (
    CapitalAllocationValidationError,
    validate_capital_allocation_input,
)
from business_quality.earnings_quality_engine import (
    EARNINGS_QUALITY_VERSION,
    EarningsQualityEngine,
)
from business_quality.earnings_quality_explainability import (
    EARNINGS_QUALITY_DISCLAIMER,
)
from business_quality.earnings_quality_models import (
    EarningsQualityAnalysis,
    EarningsQualityFlag,
)
from business_quality.earnings_quality_validation import (
    EarningsQualityValidationError,
    validate_earnings_quality_input,
)
from business_quality.engine import BusinessQualityEngine
from business_quality.exceptions import (
    BusinessQualityError,
    BusinessQualityFrameworkError,
    BusinessQualityValidationError,
)
from business_quality.explainability import (
    RESEARCH_DISCLAIMER,
    BusinessQualityExplainability,
    build_explainability,
    explainability_from_mapping,
)
from business_quality.metadata import (
    BUSINESS_QUALITY_VERSION,
    FRAMEWORK_VERSION,
    BusinessQualityMetadata,
)
from business_quality.models import (
    BusinessQualityAnalysis,
    BusinessQualityFlag,
    BusinessQualityScore,
    BusinessQualitySummary,
)
from business_quality.scoring import (
    Assessment,
    Confidence,
    EvidenceLevel,
    Rating,
    RiskLevel,
    Score,
    WeightedScore,
    clip_score,
    score_from_mapping,
    weighted_mean,
)
from business_quality.validation import (
    BusinessQualityValidation,
    empty_validation,
    merge_validation_results,
    validate_confidence,
    validate_evidence_level,
    validate_required_inputs,
)

__all__ = [
    "BUSINESS_QUALITY_VERSION",
    "CAPITAL_ALLOCATION_DISCLAIMER",
    "CAPITAL_ALLOCATION_VERSION",
    "EARNINGS_QUALITY_DISCLAIMER",
    "EARNINGS_QUALITY_VERSION",
    "FRAMEWORK_VERSION",
    "RESEARCH_DISCLAIMER",
    "Assessment",
    "BusinessQualityAnalysis",
    "BusinessQualityEngine",
    "BusinessQualityError",
    "BusinessQualityExplainability",
    "BusinessQualityFlag",
    "BusinessQualityFrameworkError",
    "BusinessQualityMetadata",
    "BusinessQualityScore",
    "BusinessQualitySummary",
    "BusinessQualityValidation",
    "BusinessQualityValidationError",
    "CapitalAllocationAnalysis",
    "CapitalAllocationEngine",
    "CapitalAllocationFlag",
    "CapitalAllocationValidationError",
    "Confidence",
    "EarningsQualityAnalysis",
    "EarningsQualityEngine",
    "EarningsQualityFlag",
    "EarningsQualityValidationError",
    "EvidenceLevel",
    "Rating",
    "RiskLevel",
    "Score",
    "WeightedScore",
    "build_explainability",
    "clip_score",
    "empty_validation",
    "explainability_from_mapping",
    "merge_validation_results",
    "score_from_mapping",
    "validate_capital_allocation_input",
    "validate_confidence",
    "validate_earnings_quality_input",
    "validate_evidence_level",
    "validate_required_inputs",
    "weighted_mean",
]

__version__ = "0.3.0"
