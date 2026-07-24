"""Portfolio package exceptions."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["PortfolioError"]


class PortfolioError(DSPAIError):
    """Raised for Portfolio domain invariant violations."""
