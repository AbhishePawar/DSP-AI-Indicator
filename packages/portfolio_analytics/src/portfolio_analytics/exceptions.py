"""portfolio_analytics package exceptions."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["PortfolioAnalyticsError"]


class PortfolioAnalyticsError(DSPAIError):
    """Raised for portfolio_analytics domain invariant violations."""
