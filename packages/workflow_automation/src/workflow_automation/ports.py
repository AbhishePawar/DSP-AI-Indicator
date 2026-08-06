"""Workflow Automation persistence port — Clean Architecture boundary.

Mirrors ``portfolio_store.ports``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from workflow_automation.models import AlertRule, Notification, ScheduledReport

__all__ = ["WorkflowAutomationStorePort"]


@runtime_checkable
class WorkflowAutomationStorePort(Protocol):
    """Durable or in-memory persistence surface for alert rules, scheduled
    reports, and notifications. Tests use
    ``InMemoryWorkflowAutomationStore``; production uses
    ``DatabaseWorkflowAutomationStore`` over a ``DatabasePort``."""

    alert_rules: dict[str, AlertRule]
    scheduled_reports: dict[str, ScheduledReport]
    notifications: dict[str, Notification]

    def clear(self) -> None: ...

    def flush(self) -> None:
        """Persist working set when backed by durable storage (no-op in memory)."""
