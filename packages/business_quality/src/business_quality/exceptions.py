"""Exceptions for the Business Quality domain."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = [
    "BusinessQualityError",
    "BusinessQualityValidationError",
    "BusinessQualityFrameworkError",
]


class BusinessQualityError(DSPAIError):
    """Base error for the business_quality package."""


class BusinessQualityValidationError(BusinessQualityError):
    """Raised when business-quality framework validation fails hard checks."""


class BusinessQualityFrameworkError(BusinessQualityError):
    """Raised when framework invariants are violated (not analysis errors)."""
