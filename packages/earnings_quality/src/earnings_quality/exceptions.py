"""Exceptions for the Earnings Quality & Predictability bounded context."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["EarningsQualityError", "EarningsQualityValidationError"]


class EarningsQualityError(DSPAIError):
    """Base error for the earnings_quality package."""


class EarningsQualityValidationError(EarningsQualityError):
    """Raised when an Earnings Quality invariant is not satisfied."""
