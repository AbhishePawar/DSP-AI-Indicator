"""Risk Intelligence package exceptions."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["RiskError"]


class RiskError(DSPAIError):
    """Raised for Risk domain invariant violations."""
