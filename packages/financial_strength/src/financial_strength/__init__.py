"""Financial Strength Intelligence public API (FEATURE-003 Phase 1)."""

from __future__ import annotations

from financial_strength.engine import FinancialStrengthEngine
from financial_strength.exceptions import (
    FinancialStrengthError,
    FinancialStrengthValidationError,
)
from financial_strength.metadata import (
    FINANCIAL_STRENGTH_VERSION,
    FRAMEWORK_VERSION,
    FinancialStrengthMetadata,
)
from financial_strength.models import (
    FinancialStrengthAnalysis,
    FinancialStrengthComponentScore,
    FinancialStrengthConfidence,
    FinancialStrengthEvidence,
    FinancialStrengthExplainability,
    FinancialStrengthScore,
    FinancialStrengthValidationSummary,
)
from financial_strength.scoring import (
    DEFAULT_STRENGTH_WEIGHTS,
    FinancialStrengthDimension,
    FinancialStrengthRating,
    FinancialStrengthWeights,
    strength_rating_from_score,
    validate_weights,
)

__all__ = [
    "DEFAULT_STRENGTH_WEIGHTS",
    "FINANCIAL_STRENGTH_VERSION",
    "FRAMEWORK_VERSION",
    "FinancialStrengthAnalysis",
    "FinancialStrengthComponentScore",
    "FinancialStrengthConfidence",
    "FinancialStrengthDimension",
    "FinancialStrengthEngine",
    "FinancialStrengthError",
    "FinancialStrengthEvidence",
    "FinancialStrengthExplainability",
    "FinancialStrengthMetadata",
    "FinancialStrengthRating",
    "FinancialStrengthScore",
    "FinancialStrengthValidationError",
    "FinancialStrengthValidationSummary",
    "FinancialStrengthWeights",
    "strength_rating_from_score",
    "validate_weights",
]

__version__ = "0.1.0"
