"""Quantitative Risk Intelligence package exceptions."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["QuantitativeRiskError"]


class QuantitativeRiskError(DSPAIError):
    """Raised for Quantitative Risk domain invariant violations."""
