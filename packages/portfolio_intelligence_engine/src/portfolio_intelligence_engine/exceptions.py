"""portfolio_intelligence_engine exceptions."""

from __future__ import annotations

__all__ = ["PortfolioIntelligenceEngineError"]


class PortfolioIntelligenceEngineError(ValueError):
    """Raised for invalid caller input to the Portfolio Intelligence Engine."""
