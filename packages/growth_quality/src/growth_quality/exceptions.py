"""Exceptions for the Growth Quality bounded context."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["GrowthQualityError", "GrowthQualityValidationError"]


class GrowthQualityError(DSPAIError):
    """Base error for the growth_quality package."""


class GrowthQualityValidationError(GrowthQualityError):
    """Raised when a Growth Quality invariant is not satisfied."""
