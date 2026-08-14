"""Workflow Automation façade (RC1 Milestone 5).

Public entry point re-exported by ``dsp_platform.platform.DSPPlatform``. See
``dsp_platform.workflow_automation.service`` for the orchestration —
CRUD delegates directly to ``workflow_automation.WorkflowAutomationService``;
``evaluate_user_alerts``/``run_scheduled_report_now`` are the only places
engine calls happen (market quotes, Portfolio Intelligence Engine, email
delivery — all frozen, all reused).
"""

from __future__ import annotations

from dsp_platform.workflow_automation.service import (
    WORKFLOW_AUTOMATION_SERVICE_VERSION,
    configure_workflow_automation_store,
    create_alert_rule,
    create_scheduled_report,
    delete_alert_rule,
    delete_scheduled_report,
    evaluate_user_alerts,
    get_alert_rule,
    get_scheduled_report,
    list_alert_rules,
    list_notifications,
    list_scheduled_reports,
    mark_notification_read,
    reset_workflow_automation_for_tests,
    run_scheduled_report_now,
    update_alert_rule,
    update_scheduled_report,
    workflow_automation_health,
    workflow_automation_schema,
)

__all__ = [
    "WORKFLOW_AUTOMATION_SERVICE_VERSION",
    "configure_workflow_automation_store",
    "create_alert_rule",
    "create_scheduled_report",
    "delete_alert_rule",
    "delete_scheduled_report",
    "evaluate_user_alerts",
    "get_alert_rule",
    "get_scheduled_report",
    "list_alert_rules",
    "list_notifications",
    "list_scheduled_reports",
    "mark_notification_read",
    "reset_workflow_automation_for_tests",
    "run_scheduled_report_now",
    "update_alert_rule",
    "update_scheduled_report",
    "workflow_automation_health",
    "workflow_automation_schema",
]
