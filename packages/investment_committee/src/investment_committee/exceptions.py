"""Exceptions for the Investment Committee bounded context (FEATURE-008)."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["InvestmentCommitteeError", "InvestmentCommitteeValidationError"]


class InvestmentCommitteeError(DSPAIError):
    """Base error for the investment_committee package."""


class InvestmentCommitteeValidationError(InvestmentCommitteeError):
    """Raised when a committee invariant is not satisfied."""
