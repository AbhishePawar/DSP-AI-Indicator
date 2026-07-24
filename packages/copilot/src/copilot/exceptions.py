"""AI Copilot package exceptions."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["CopilotError"]


class CopilotError(DSPAIError):
    """Raised for AI Copilot domain invariant violations."""
