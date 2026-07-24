"""Exceptions for Recommendation Intelligence."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["RecommendationError", "RecommendationMappingError"]


class RecommendationError(DSPAIError):
    """Raised for Recommendation Intelligence domain invariant violations."""


class RecommendationMappingError(DSPAIError):
    """Raised when a committee report cannot be mapped to contracts.Recommendation."""
