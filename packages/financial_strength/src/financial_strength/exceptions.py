"""Exceptions for the Financial Strength bounded context."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["FinancialStrengthError", "FinancialStrengthValidationError"]


class FinancialStrengthError(DSPAIError):
    """Base error for the financial_strength package."""


class FinancialStrengthValidationError(FinancialStrengthError):
    """Raised when a Financial Strength invariant is not satisfied."""
