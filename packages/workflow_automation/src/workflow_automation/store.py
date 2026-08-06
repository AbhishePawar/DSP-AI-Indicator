"""In-memory Workflow Automation store — process-local foundation / test adapter."""

from __future__ import annotations

from threading import Lock

from workflow_automation.models import AlertRule, Notification, ScheduledReport

__all__ = ["InMemoryWorkflowAutomationStore"]


class InMemoryWorkflowAutomationStore:
    """Thread-safe in-memory persistence for Workflow Automation domain objects.

    Implements ``WorkflowAutomationStorePort``. Prefer
    ``DatabaseWorkflowAutomationStore`` for production durability, mirroring
    ``portfolio_store.InMemoryPortfolioStore`` / ``DatabasePortfolioStore``.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self.alert_rules: dict[str, AlertRule] = {}
        self.scheduled_reports: dict[str, ScheduledReport] = {}
        self.notifications: dict[str, Notification] = {}

    def clear(self) -> None:
        with self._lock:
            self.alert_rules.clear()
            self.scheduled_reports.clear()
            self.notifications.clear()

    def flush(self) -> None:
        """No-op — in-memory adapter has no durable backend."""
