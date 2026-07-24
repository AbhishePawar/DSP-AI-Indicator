"""Industry Identity package exceptions."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["IndustryError"]


class IndustryError(DSPAIError):
    """Raised for invalid industry identity, hierarchy, or mapping state."""
