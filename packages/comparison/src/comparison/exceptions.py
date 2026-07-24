"""Comparison package exceptions."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["ComparisonError"]


class ComparisonError(DSPAIError):
    """Raised for invalid comparison requests or engine configuration."""
