"""Exceptions for the Economic Moat Intelligence bounded context."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["EconomicMoatError", "EconomicMoatValidationError"]


class EconomicMoatError(DSPAIError):
    """Base error for the economic_moat package."""


class EconomicMoatValidationError(EconomicMoatError):
    """Raised when an Economic Moat framework invariant is not satisfied."""
