"""Decision Intelligence exceptions."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["DecisionIntelligenceError"]


class DecisionIntelligenceError(DSPAIError):
    """Raised when a Decision Pack cannot be synthesized."""
