"""Exceptions for the Investment Recommendation bounded context."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = [
    "InvestmentRecommendationError",
    "InvestmentRecommendationValidationError",
]


class InvestmentRecommendationError(DSPAIError):
    """Base error for the investment_recommendation package."""


class InvestmentRecommendationValidationError(InvestmentRecommendationError):
    """Raised when a recommendation invariant is not satisfied."""
