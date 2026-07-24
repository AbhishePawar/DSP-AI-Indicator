"""Recommendation Intelligence public API (G1.3 — models + assembler + engine + reporter).

Legacy Sprint 7.1 ``RecommendationMapper`` remains exported as a committee
adapter and is not part of the Recommendation Intelligence engine surface.
"""

from __future__ import annotations

from recommendation.assembler import (
    AssemblyContext,
    AssemblyResult,
    RecommendationAssembler,
)
from recommendation.engine import EngineContext, EngineResult, RecommendationEngine
from recommendation.enums import (
    AssemblyStatus,
    ConfidenceLevel,
    ConflictSeverity,
    EngineStatus,
    RecommendationType,
    ReportingStatus,
    SignalPosture,
)
from recommendation.exceptions import RecommendationError, RecommendationMappingError
from recommendation.mapper import RecommendationMapper
from recommendation.models import (
    RecommendationConflict,
    RecommendationIdentity,
    RecommendationOption,
    RecommendationProfile,
    RecommendationRationale,
    RecommendationReport,
    RecommendationScore,
    RecommendationSummary,
)
from recommendation.refs import (
    ComparisonReference,
    DecisionReference,
    PortfolioReference,
    QuantitativeRiskReference,
    ResearchReference,
    RiskReference,
)
from recommendation.reporter import (
    CitationSection,
    RecommendationReporter,
    ReportMetadata,
    ReportingContext,
    ReportingResult,
)

__all__ = [
    "AssemblyContext",
    "AssemblyResult",
    "AssemblyStatus",
    "CitationSection",
    "ComparisonReference",
    "ConfidenceLevel",
    "ConflictSeverity",
    "DecisionReference",
    "EngineContext",
    "EngineResult",
    "EngineStatus",
    "PortfolioReference",
    "QuantitativeRiskReference",
    "RecommendationAssembler",
    "RecommendationConflict",
    "RecommendationEngine",
    "RecommendationError",
    "RecommendationIdentity",
    "RecommendationMapper",
    "RecommendationMappingError",
    "RecommendationOption",
    "RecommendationProfile",
    "RecommendationRationale",
    "RecommendationReport",
    "RecommendationReporter",
    "RecommendationScore",
    "RecommendationSummary",
    "RecommendationType",
    "ReportMetadata",
    "ReportingContext",
    "ReportingResult",
    "ReportingStatus",
    "ResearchReference",
    "RiskReference",
    "SignalPosture",
]

__version__ = "0.4.0"
