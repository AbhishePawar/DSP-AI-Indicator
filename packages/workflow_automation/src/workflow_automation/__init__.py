"""workflow_automation — RC1 Milestone 5.

Server-side, user-owned persistence and evaluation logic for Alert Rules,
Scheduled Reports, and the Notification Center. See the package README for
the full data-honesty contract and the explicit "no autonomous scheduler"
boundary.
"""

from __future__ import annotations

from workflow_automation.enums import (
    AlertRuleType,
    AlertStatus,
    NotificationKind,
    ScheduleFormat,
    ScheduleFrequency,
)
from workflow_automation.evaluation import (
    AlertEvaluation,
    evaluate_earnings_alert,
    evaluate_price_alert,
    evaluate_research_stale_alert,
    evaluate_valuation_alert,
)
from workflow_automation.exceptions import (
    ForbiddenError,
    NotFoundError,
    ValidationError,
    WorkflowAutomationError,
)
from workflow_automation.models import (
    WORKFLOW_AUTOMATION_SCHEMA_VERSION,
    WORKFLOW_AUTOMATION_SERVICE_VERSION,
    AlertRule,
    Notification,
    ScheduledReport,
)
from workflow_automation.service import (
    WorkflowAutomationService,
    get_workflow_automation_service,
    reset_workflow_automation_service_for_tests,
)
from workflow_automation.store import InMemoryWorkflowAutomationStore

__version__ = "0.1.0"

__all__ = [
    "WORKFLOW_AUTOMATION_SCHEMA_VERSION",
    "WORKFLOW_AUTOMATION_SERVICE_VERSION",
    "AlertEvaluation",
    "AlertRule",
    "AlertRuleType",
    "AlertStatus",
    "ForbiddenError",
    "InMemoryWorkflowAutomationStore",
    "Notification",
    "NotificationKind",
    "NotFoundError",
    "ScheduleFormat",
    "ScheduleFrequency",
    "ScheduledReport",
    "ValidationError",
    "WorkflowAutomationError",
    "WorkflowAutomationService",
    "__version__",
    "evaluate_earnings_alert",
    "evaluate_price_alert",
    "evaluate_research_stale_alert",
    "evaluate_valuation_alert",
    "get_workflow_automation_service",
    "reset_workflow_automation_service_for_tests",
]
