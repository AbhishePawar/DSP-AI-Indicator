"""Workflow Intelligence package exceptions."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["WorkflowError"]


class WorkflowError(DSPAIError):
    """Raised for Workflow Intelligence domain invariant violations."""
