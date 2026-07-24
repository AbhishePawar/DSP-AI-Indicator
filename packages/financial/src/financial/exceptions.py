"""Exceptions for the Financial Statement Domain."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = [
    "FinancialError",
    "FinancialValidationError",
    "IncomeAnalysisError",
    "BalanceAnalysisError",
    "CashFlowAnalysisError",
    "FinancialRatioError",
    "TrendAnalysisError",
    "FinancialAggregationError",
]


class FinancialError(DSPAIError):
    """Base error for the financial domain package."""


class FinancialValidationError(FinancialError):
    """Raised when financial statement validation fails hard checks."""


class IncomeAnalysisError(FinancialError):
    """Raised when Income Statement Intelligence inputs fail hard checks."""


class BalanceAnalysisError(FinancialError):
    """Raised when Balance Sheet Intelligence inputs fail hard checks."""


class CashFlowAnalysisError(FinancialError):
    """Raised when Cash Flow Intelligence inputs fail hard checks."""


class FinancialRatioError(FinancialError):
    """Raised when Financial Ratio Engine inputs fail hard checks."""


class TrendAnalysisError(FinancialError):
    """Raised when Trend & Time-Series Intelligence inputs fail hard checks."""


class FinancialAggregationError(FinancialError):
    """Raised when Financial Statement Aggregator inputs fail hard checks."""
