"""Economic Moat Intelligence public API (FEATURE-001 Phase 1)."""

from __future__ import annotations

from economic_moat.engine import EconomicEngine
from economic_moat.exceptions import EconomicMoatError, EconomicMoatValidationError
from economic_moat.metadata import ECONOMIC_MOAT_VERSION, FRAMEWORK_VERSION, EconomicMetadata
from economic_moat.models import (
    EconomicAnalysis,
    EconomicConfidence,
    EconomicEvidence,
    EconomicExplainability,
    EconomicScore,
    EconomicValidationSummary,
    MoatComponentScore,
)
from economic_moat.scoring import (
    DEFAULT_MOAT_WEIGHTS,
    MoatDimension,
    MoatRating,
    MoatWeights,
    moat_rating_from_score,
    validate_weights,
)

__all__ = [
    "DEFAULT_MOAT_WEIGHTS",
    "ECONOMIC_MOAT_VERSION",
    "FRAMEWORK_VERSION",
    "EconomicAnalysis",
    "EconomicConfidence",
    "EconomicEngine",
    "EconomicEvidence",
    "EconomicExplainability",
    "EconomicMetadata",
    "EconomicMoatError",
    "EconomicMoatValidationError",
    "EconomicScore",
    "EconomicValidationSummary",
    "MoatComponentScore",
    "MoatDimension",
    "MoatRating",
    "MoatWeights",
    "moat_rating_from_score",
    "validate_weights",
]

__version__ = "0.2.0"
