"""Research Intelligence package exceptions."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["ResearchError"]


class ResearchError(DSPAIError):
    """Raised for Research domain invariant violations."""
