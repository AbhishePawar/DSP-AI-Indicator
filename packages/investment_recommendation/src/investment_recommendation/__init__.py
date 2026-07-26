"""Investment Recommendation public API (FEATURE-007 Phase 1).

Deterministic decision intelligence from valuation + domain quality engines.
Distinct from G1.3 ``recommendation.RecommendationEngine``.
"""

from __future__ import annotations

from investment_recommendation.engine import InvestmentRecommendationEngine
from investment_recommendation.exceptions import (
    InvestmentRecommendationError,
    InvestmentRecommendationValidationError,
)
from investment_recommendation.metadata import (
    FRAMEWORK_VERSION,
    RECOMMENDATION_VERSION,
    InvestmentRecommendationMetadata,
)
from investment_recommendation.models import (
    DecisionContribution,
    InvestmentRecommendation,
    InvestmentRecommendationConfidence,
    InvestmentRecommendationEvidence,
    InvestmentRecommendationExplainability,
    InvestmentRecommendationScore,
    InvestmentRecommendationValidationSummary,
    MarginOfSafetyAssessment,
    TriggeredRule,
)
from investment_recommendation.scoring import (
    DEFAULT_DECISION_WEIGHTS,
    DecisionComponent,
    DecisionWeights,
    InvestmentRecommendationAction,
    action_from_score,
    validate_weights,
)
from investment_recommendation.valuation_signals import ValuationSignals

__all__ = [
    "DEFAULT_DECISION_WEIGHTS",
    "FRAMEWORK_VERSION",
    "RECOMMENDATION_VERSION",
    "DecisionComponent",
    "DecisionContribution",
    "DecisionWeights",
    "InvestmentRecommendation",
    "InvestmentRecommendationAction",
    "InvestmentRecommendationConfidence",
    "InvestmentRecommendationEngine",
    "InvestmentRecommendationError",
    "InvestmentRecommendationEvidence",
    "InvestmentRecommendationExplainability",
    "InvestmentRecommendationMetadata",
    "InvestmentRecommendationScore",
    "InvestmentRecommendationValidationError",
    "InvestmentRecommendationValidationSummary",
    "MarginOfSafetyAssessment",
    "TriggeredRule",
    "ValuationSignals",
    "action_from_score",
    "validate_weights",
]

__version__ = "0.1.0"
