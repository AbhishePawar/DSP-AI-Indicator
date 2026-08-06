"""Workflow Automation routes (RC1 Milestone 5).

Thin, additive, authenticated routes over ``dsp_platform``'s Workflow
Automation façade — Alert Rules, Scheduled Reports, and the Notification
Center. Every route requires the existing institutional auth
(``get_current_user_id`` — EPIC-A009, no new auth scheme) and enforces
ownership via ``user_id``. No business logic, market-data, or valuation
here — evaluation reuses ``market_quotes``/``portfolio_intelligence_engine``
entirely inside ``dsp_platform``.

Mounted under ``/workflow-automation`` — deliberately not ``/workflow``,
which already hosts the frozen H1 Workflow Engine
(``POST /workflow/run``) and the EPIC-A007 institutional approval routes
(``/workflow/schema``, ``/workflow/templates``, ``/workflow/action``), both
distinct, unrelated capabilities.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_platform.api.dependencies import ApiState, get_api_state, get_current_user_id
from workflow_automation import ForbiddenError, NotFoundError, ValidationError

router = APIRouter(tags=["workflow-automation"])


def _error_response(exc: Exception) -> JSONResponse:
    if isinstance(exc, NotFoundError):
        status = 404
    elif isinstance(exc, ForbiddenError):
        status = 403
    elif isinstance(exc, ValidationError):
        status = 400
    else:
        status = 503
    return JSONResponse(
        status_code=status,
        content={"ok": False, "error": str(exc), "message": "Data unavailable."},
    )


class CreateAlertRuleRequest(BaseModel):
    rule_type: str = Field(..., min_length=1, max_length=64)
    symbol: str | None = Field(None, max_length=32)
    portfolio_id: str | None = Field(None, max_length=64)
    params: dict[str, Any] | None = None
    active: bool = True


class UpdateAlertRuleRequest(BaseModel):
    active: bool | None = None
    params: dict[str, Any] | None = None


class CreateScheduledReportRequest(BaseModel):
    portfolio_id: str = Field(..., min_length=1, max_length=64)
    frequency: str = Field(..., min_length=1, max_length=32)
    format: str = Field("json", max_length=16)
    recipients: list[str] | None = None
    active: bool = True


class UpdateScheduledReportRequest(BaseModel):
    active: bool | None = None
    frequency: str | None = Field(None, max_length=32)
    format: str | None = Field(None, max_length=16)
    recipients: list[str] | None = None


class EvaluateAlertsRequest(BaseModel):
    research_objects: dict[str, Any] | list[Any] | None = None


class RunScheduledReportRequest(BaseModel):
    research_objects: dict[str, Any] | list[Any] | None = None


@router.get("/workflow-automation/schema")
def workflow_automation_schema_route(
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    return {"ok": True, "schema": state.platform.workflow_automation_schema()}


@router.get("/workflow-automation/health")
def workflow_automation_health_route(
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    return {"ok": True, "health": state.platform.workflow_automation_health()}


# ---------------------------------------------------------------- alert rules
@router.get("/workflow-automation/alerts")
def list_alert_rules_route(
    active_only: bool = False,
    user_id: str = Depends(get_current_user_id),
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    rows = state.platform.list_alert_rules(user_id=user_id, active_only=active_only)
    return {"ok": True, "rules": rows}


@router.post("/workflow-automation/alerts")
def create_alert_rule_route(
    body: CreateAlertRuleRequest,
    user_id: str = Depends(get_current_user_id),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    try:
        rule = state.platform.create_alert_rule(
            user_id=user_id,
            rule_type=body.rule_type,
            symbol=body.symbol,
            portfolio_id=body.portfolio_id,
            params=body.params,
            active=body.active,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "rule": rule})


@router.get("/workflow-automation/alerts/{rule_id}")
def get_alert_rule_route(
    rule_id: str,
    user_id: str = Depends(get_current_user_id),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    try:
        rule = state.platform.get_alert_rule(rule_id, user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "rule": rule})


@router.put("/workflow-automation/alerts/{rule_id}")
def update_alert_rule_route(
    rule_id: str,
    body: UpdateAlertRuleRequest,
    user_id: str = Depends(get_current_user_id),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    try:
        rule = state.platform.update_alert_rule(
            rule_id, user_id=user_id, active=body.active, params=body.params
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "rule": rule})


@router.delete("/workflow-automation/alerts/{rule_id}")
def delete_alert_rule_route(
    rule_id: str,
    user_id: str = Depends(get_current_user_id),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    try:
        state.platform.delete_alert_rule(rule_id, user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True})


@router.post("/workflow-automation/alerts/evaluate")
def evaluate_alerts_route(
    body: EvaluateAlertsRequest,
    user_id: str = Depends(get_current_user_id),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """On-demand evaluation trigger — no autonomous scheduler exists at this
    boundary (see docs/WORKFLOW_AUTOMATION_GUIDE.md); the caller (frontend
    "Check Now" action, or an external cron hitting this endpoint) drives
    every evaluation."""
    try:
        result = state.platform.evaluate_user_alerts(
            user_id=user_id, research_objects=body.research_objects
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, **result})


# ------------------------------------------------------------ scheduled reports
@router.get("/workflow-automation/schedules")
def list_scheduled_reports_route(
    user_id: str = Depends(get_current_user_id),
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    rows = state.platform.list_scheduled_reports(user_id=user_id)
    return {"ok": True, "schedules": rows}


@router.post("/workflow-automation/schedules")
def create_scheduled_report_route(
    body: CreateScheduledReportRequest,
    user_id: str = Depends(get_current_user_id),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    try:
        schedule = state.platform.create_scheduled_report(
            user_id=user_id,
            portfolio_id=body.portfolio_id,
            frequency=body.frequency,
            format=body.format,
            recipients=body.recipients,
            active=body.active,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "schedule": schedule})


@router.get("/workflow-automation/schedules/{schedule_id}")
def get_scheduled_report_route(
    schedule_id: str,
    user_id: str = Depends(get_current_user_id),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    try:
        schedule = state.platform.get_scheduled_report(schedule_id, user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "schedule": schedule})


@router.put("/workflow-automation/schedules/{schedule_id}")
def update_scheduled_report_route(
    schedule_id: str,
    body: UpdateScheduledReportRequest,
    user_id: str = Depends(get_current_user_id),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    try:
        schedule = state.platform.update_scheduled_report(
            schedule_id,
            user_id=user_id,
            active=body.active,
            frequency=body.frequency,
            format=body.format,
            recipients=body.recipients,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "schedule": schedule})


@router.delete("/workflow-automation/schedules/{schedule_id}")
def delete_scheduled_report_route(
    schedule_id: str,
    user_id: str = Depends(get_current_user_id),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    try:
        state.platform.delete_scheduled_report(schedule_id, user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True})


@router.post("/workflow-automation/schedules/{schedule_id}/run")
def run_scheduled_report_route(
    schedule_id: str,
    body: RunScheduledReportRequest,
    user_id: str = Depends(get_current_user_id),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Manually run a Scheduled Report definition now — the only implemented
    execution path (no autonomous cron at this boundary)."""
    try:
        result = state.platform.run_scheduled_report_now(
            schedule_id, user_id=user_id, research_objects=body.research_objects
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, **result})


# --------------------------------------------------------------- notifications
@router.get("/workflow-automation/notifications")
def list_notifications_route(
    unread_only: bool = False,
    limit: int = 200,
    user_id: str = Depends(get_current_user_id),
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    rows = state.platform.list_notifications(
        user_id=user_id, unread_only=unread_only, limit=limit
    )
    return {"ok": True, "notifications": rows}


@router.post("/workflow-automation/notifications/{notification_id}/read")
def mark_notification_read_route(
    notification_id: str,
    user_id: str = Depends(get_current_user_id),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    try:
        notification = state.platform.mark_notification_read(
            notification_id, user_id=user_id
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "notification": notification})
