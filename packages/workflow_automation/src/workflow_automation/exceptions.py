"""workflow_automation domain exceptions (mirrors portfolio_store.exceptions)."""

from __future__ import annotations

__all__ = [
    "ForbiddenError",
    "NotFoundError",
    "ValidationError",
    "WorkflowAutomationError",
]


class WorkflowAutomationError(Exception):
    """Base workflow_automation error."""


class ValidationError(WorkflowAutomationError):
    """Invalid input or state transition."""


class NotFoundError(WorkflowAutomationError):
    """Requested alert rule / schedule / notification does not exist."""


class ForbiddenError(WorkflowAutomationError):
    """The requesting user does not own the requested resource."""
