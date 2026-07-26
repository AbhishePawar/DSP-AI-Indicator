"""Exceptions for the Management Quality bounded context."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["ManagementQualityError", "ManagementQualityValidationError"]


class ManagementQualityError(DSPAIError):
    """Base error for the management_quality package."""


class ManagementQualityValidationError(ManagementQualityError):
    """Raised when a Management Quality invariant is not satisfied."""
