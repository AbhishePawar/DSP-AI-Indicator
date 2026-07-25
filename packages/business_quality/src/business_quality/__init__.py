"""Canonical Business Quality Intelligence — public package surface.

Phase 3 / F3.1–F3.7: framework + module intelligence + engine + aggregator.
Consumes FinancialAnalysis (engine) / BusinessQualityAnalysis (aggregator).
"""

from __future__ import annotations

from business_quality.business_characteristics_engine import (
    BUSINESS_CHARACTERISTICS_VERSION,
    BusinessCharacteristicsEngine,
)
from business_quality.business_characteristics_explainability import (
    BUSINESS_CHARACTERISTICS_DISCLAIMER,
)
from business_quality.business_characteristics_models import (
    BusinessCharacteristicsAnalysis,
    BusinessCharacteristicsFlag,
)
from business_quality.business_characteristics_validation import (
    BusinessCharacteristicsValidationError,
    validate_business_characteristics_input,
)
from business_quality.business_quality_aggregator import (
    BUSINESS_QUALITY_AGGREGATOR_VERSION,
    BusinessQualityAggregator,
)
from business_quality.business_quality_engine import (
    BUSINESS_QUALITY_ENGINE_VERSION,
    BusinessQualityEngine,
    aggregate_flags,
    compose_overall_score,
    overall_rating_from_01,
)
from business_quality.business_quality_explainability import (
    BUSINESS_QUALITY_ENGINE_DISCLAIMER,
)
from business_quality.business_quality_report_explainability import (
    BUSINESS_QUALITY_AGGREGATOR_DISCLAIMER,
)
from business_quality.business_quality_report_models import (
    BusinessQualityReport,
    ConfidenceSummary,
    ModuleBreakdownEntry,
    ReportSignal,
)
from business_quality.business_quality_report_validation import (
    BusinessQualityReportValidationError,
    validate_business_quality_analysis,
    validate_report_metadata,
    validate_report_object,
)
from business_quality.business_quality_summary import (
    build_confidence_summary,
    build_executive_summary,
    build_module_breakdown,
    build_recommended_interpretation,
    dedupe_ordered,
)
from business_quality.business_quality_validation import (
    BusinessQualityEngineValidationError,
    validate_business_quality_input,
    validate_module_outputs,
    validate_weights,
)
from business_quality.models import (
    AggregatedFlag,
    AggregatedFlags,
    BusinessQualityAnalysis,
    BusinessQualityFlag,
    BusinessQualityScore,
    BusinessQualitySummary,
    BusinessQualityWeights,
    DEFAULT_BUSINESS_QUALITY_WEIGHTS,
    FlagSeverity,
    OverallAssessment,
    OverallRating,
)
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
from business_quality.competitive_position_engine import (
    COMPETITIVE_POSITION_VERSION,
    CompetitivePositionEngine,
)
from business_quality.competitive_position_explainability import (
    COMPETITIVE_POSITION_DISCLAIMER,
)
from business_quality.competitive_position_models import (
    CompetitivePositionAnalysis,
    CompetitivePositionFlag,
)
from business_quality.competitive_position_validation import (
    CompetitivePositionValidationError,
    validate_competitive_position_input,
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
    "BUSINESS_CHARACTERISTICS_DISCLAIMER",
    "BUSINESS_CHARACTERISTICS_VERSION",
    "BUSINESS_QUALITY_AGGREGATOR_DISCLAIMER",
    "BUSINESS_QUALITY_AGGREGATOR_VERSION",
    "BUSINESS_QUALITY_ENGINE_DISCLAIMER",
    "BUSINESS_QUALITY_ENGINE_VERSION",
    "BUSINESS_QUALITY_VERSION",
    "CAPITAL_ALLOCATION_DISCLAIMER",
    "CAPITAL_ALLOCATION_VERSION",
    "COMPETITIVE_POSITION_DISCLAIMER",
    "COMPETITIVE_POSITION_VERSION",
    "DEFAULT_BUSINESS_QUALITY_WEIGHTS",
    "EARNINGS_QUALITY_DISCLAIMER",
    "EARNINGS_QUALITY_VERSION",
    "FRAMEWORK_VERSION",
    "RESEARCH_DISCLAIMER",
    "AggregatedFlag",
    "AggregatedFlags",
    "Assessment",
    "BusinessCharacteristicsAnalysis",
    "BusinessCharacteristicsEngine",
    "BusinessCharacteristicsFlag",
    "BusinessCharacteristicsValidationError",
    "BusinessQualityAggregator",
    "BusinessQualityAnalysis",
    "BusinessQualityEngine",
    "BusinessQualityEngineValidationError",
    "BusinessQualityError",
    "BusinessQualityExplainability",
    "BusinessQualityFlag",
    "BusinessQualityFrameworkError",
    "BusinessQualityMetadata",
    "BusinessQualityReport",
    "BusinessQualityReportValidationError",
    "BusinessQualityScore",
    "BusinessQualitySummary",
    "BusinessQualityValidation",
    "BusinessQualityValidationError",
    "BusinessQualityWeights",
    "CapitalAllocationAnalysis",
    "CapitalAllocationEngine",
    "CapitalAllocationFlag",
    "CapitalAllocationValidationError",
    "CompetitivePositionAnalysis",
    "CompetitivePositionEngine",
    "CompetitivePositionFlag",
    "CompetitivePositionValidationError",
    "Confidence",
    "ConfidenceSummary",
    "EarningsQualityAnalysis",
    "EarningsQualityEngine",
    "EarningsQualityFlag",
    "EarningsQualityValidationError",
    "EvidenceLevel",
    "FlagSeverity",
    "ModuleBreakdownEntry",
    "OverallAssessment",
    "OverallRating",
    "Rating",
    "ReportSignal",
    "RiskLevel",
    "Score",
    "WeightedScore",
    "aggregate_flags",
    "build_confidence_summary",
    "build_executive_summary",
    "build_explainability",
    "build_module_breakdown",
    "build_recommended_interpretation",
    "clip_score",
    "compose_overall_score",
    "dedupe_ordered",
    "empty_validation",
    "explainability_from_mapping",
    "merge_validation_results",
    "overall_rating_from_01",
    "score_from_mapping",
    "validate_business_characteristics_input",
    "validate_business_quality_analysis",
    "validate_business_quality_input",
    "validate_capital_allocation_input",
    "validate_competitive_position_input",
    "validate_confidence",
    "validate_earnings_quality_input",
    "validate_evidence_level",
    "validate_module_outputs",
    "validate_report_metadata",
    "validate_report_object",
    "validate_required_inputs",
    "validate_weights",
    "weighted_mean",
]

__version__ = "0.7.0"
