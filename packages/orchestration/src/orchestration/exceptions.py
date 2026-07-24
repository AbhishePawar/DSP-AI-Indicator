"""Orchestration-layer exceptions."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["OrchestrationError"]


class OrchestrationError(DSPAIError):
    """Raised when the analysis pipeline fails at the application layer.

    Wraps provider, bridge, engine, and committee failures so callers
    catch one hierarchy and never see vendor-specific exceptions.
    """
