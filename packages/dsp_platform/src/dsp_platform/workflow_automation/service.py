"""Workflow Automation — orchestration (RC1 Milestone 5).

CRUD (alert rules, scheduled reports, notifications) delegates directly to
``workflow_automation.WorkflowAutomationService`` — no business logic here.

Two functions are the **only** place engine calls happen:

- ``evaluate_user_alerts`` — for each of the user's active alert rules,
  fetches the already-computed signal from a frozen engine
  (``dsp_platform.market_quotes`` for price alerts,
  ``dsp_platform.portfolio_store_facade`` + ``portfolio_intelligence_engine``
  for valuation alerts), calls the pure ``workflow_automation.evaluate_*``
  comparison, and — only on a transition into "triggered" — creates a
  Notification and best-effort sends an email via the existing
  ``auth.email_delivery.EmailProviderPort`` (no new delivery channel).
- ``run_scheduled_report_now`` — the only implemented execution path for a
  Scheduled Report definition (no autonomous scheduler exists at the
  ``dsp_platform`` boundary — see package README). Reuses
  ``portfolio_store_facade`` + ``portfolio_intelligence_engine`` to build the
  snapshot, then serializes it (pure formatting, not a new export engine).
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping
from typing import Any

from workflow_automation import get_workflow_automation_service
from workflow_automation import (
    reset_workflow_automation_service_for_tests as _reset_service,
)
from workflow_automation.enums import AlertStatus
from workflow_automation.evaluation import (
    AlertEvaluation,
    evaluate_earnings_alert,
    evaluate_price_alert,
    evaluate_research_stale_alert,
    evaluate_valuation_alert,
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

WORKFLOW_AUTOMATION_SERVICE_VERSION = "1.0.0"


def configure_workflow_automation_store(*, database: Any | None = None) -> None:
    """Wire a durable ``DatabasePort`` into the process-local singleton.

    Safe to call multiple times / with ``database=None`` — mirrors
    ``dsp_platform.portfolio_store_facade.configure_portfolio_store``.
    """
    get_workflow_automation_service(database=database)


def workflow_automation_schema() -> dict[str, Any]:
    return get_workflow_automation_service().schema()


# ---------------------------------------------------------------- alert rules
def create_alert_rule(
    *,
    user_id: str,
    rule_type: str,
    symbol: str | None = None,
    portfolio_id: str | None = None,
    params: Mapping[str, Any] | None = None,
    active: bool = True,
) -> dict[str, Any]:
    return get_workflow_automation_service().create_alert_rule(
        user_id=user_id,
        rule_type=rule_type,
        symbol=symbol,
        portfolio_id=portfolio_id,
        params=params,
        active=active,
    )


def list_alert_rules(
    *, user_id: str, active_only: bool = False
) -> list[dict[str, Any]]:
    return get_workflow_automation_service().list_alert_rules(
        user_id=user_id, active_only=active_only
    )


def get_alert_rule(rule_id: str, *, user_id: str) -> dict[str, Any]:
    return get_workflow_automation_service().get_alert_rule(rule_id, user_id=user_id)


def update_alert_rule(
    rule_id: str,
    *,
    user_id: str,
    active: bool | None = None,
    params: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return get_workflow_automation_service().update_alert_rule(
        rule_id, user_id=user_id, active=active, params=params
    )


def delete_alert_rule(rule_id: str, *, user_id: str) -> bool:
    return get_workflow_automation_service().delete_alert_rule(rule_id, user_id=user_id)


# ------------------------------------------------------------ scheduled reports
def create_scheduled_report(
    *,
    user_id: str,
    portfolio_id: str,
    frequency: str,
    format: str = "json",
    recipients: list[str] | None = None,
    active: bool = True,
) -> dict[str, Any]:
    return get_workflow_automation_service().create_scheduled_report(
        user_id=user_id,
        portfolio_id=portfolio_id,
        frequency=frequency,
        format=format,
        recipients=recipients,
        active=active,
    )


def list_scheduled_reports(*, user_id: str) -> list[dict[str, Any]]:
    return get_workflow_automation_service().list_scheduled_reports(user_id=user_id)


def get_scheduled_report(schedule_id: str, *, user_id: str) -> dict[str, Any]:
    return get_workflow_automation_service().get_scheduled_report(
        schedule_id, user_id=user_id
    )


def update_scheduled_report(
    schedule_id: str,
    *,
    user_id: str,
    active: bool | None = None,
    frequency: str | None = None,
    format: str | None = None,
    recipients: list[str] | None = None,
) -> dict[str, Any]:
    return get_workflow_automation_service().update_scheduled_report(
        schedule_id,
        user_id=user_id,
        active=active,
        frequency=frequency,
        format=format,
        recipients=recipients,
    )


def delete_scheduled_report(schedule_id: str, *, user_id: str) -> bool:
    return get_workflow_automation_service().delete_scheduled_report(
        schedule_id, user_id=user_id
    )


# --------------------------------------------------------------- notifications
def list_notifications(
    *, user_id: str, unread_only: bool = False, limit: int = 200
) -> list[dict[str, Any]]:
    return get_workflow_automation_service().list_notifications(
        user_id=user_id, unread_only=unread_only, limit=limit
    )


def mark_notification_read(notification_id: str, *, user_id: str) -> dict[str, Any]:
    return get_workflow_automation_service().mark_notification_read(
        notification_id, user_id=user_id
    )


# ----------------------------------------------------------- alert evaluation
def _current_price(symbol: str) -> float | None:
    from dsp_platform.market_quotes import get_authenticated_market_quote

    quote = get_authenticated_market_quote(symbol)
    if quote is None:
        return None
    fields = quote.get("fields") or {}
    price = fields.get("current_price")
    return float(price) if isinstance(price, (int, float)) else None


def _valuation_classes_for_portfolio(
    portfolio_id: str,
    *,
    user_id: str,
    research_objects: Mapping[str, Any] | list[Any] | None,
) -> dict[str, str]:
    """Symbol -> valuation_class map, reusing the Portfolio Intelligence Engine."""
    from dsp_platform.portfolio_intelligence_engine import (
        evaluate_portfolio_intelligence_engine,
    )
    from dsp_platform.portfolio_store_facade import list_portfolio_holdings

    try:
        holdings = list_portfolio_holdings(portfolio_id, user_id=user_id)
    except Exception:  # noqa: BLE001 — honest unavailable, never a hard failure
        return {}
    if not holdings:
        return {}
    portfolio = {
        "holdings": [
            {"symbol": h["symbol"], "weight": h["weight"], "sector": h.get("sector")}
            for h in holdings
        ]
    }
    result = evaluate_portfolio_intelligence_engine(
        portfolio, research_objects=research_objects
    )
    if not result.get("available"):
        return {}
    heatmap = result.get("valuation_heatmap") or {}
    return {row["symbol"]: row["valuation_class"] for row in heatmap.get("rows", [])}


def _maybe_notify(
    *,
    user_id: str,
    rule: Mapping[str, Any],
    evaluation: AlertEvaluation,
) -> dict[str, Any] | None:
    """Create a Notification (and best-effort email) only on a transition
    into "triggered" — never on every re-evaluation of an already-triggered
    rule, to avoid notification spam."""
    if evaluation.status.value != "triggered" or rule.get("last_status") == "triggered":
        return None
    service = get_workflow_automation_service()
    notification = service.create_notification(
        user_id=user_id,
        kind="alert",
        title=f"Alert triggered: {rule.get('symbol') or rule.get('portfolio_id')}",
        message=evaluation.message,
        related_rule_id=rule["rule_id"],
    )
    notify_email = (rule.get("params") or {}).get("notify_email")
    if notify_email:
        try:
            from auth.email_delivery import build_email_provider

            provider = build_email_provider()
            if provider.is_available():
                provider.send(
                    to=str(notify_email),
                    subject=notification["title"],
                    body=evaluation.message,
                    purpose="workflow_alert",
                )
        except Exception:  # noqa: BLE001 — notification already recorded; email is best-effort
            pass
    return notification


def evaluate_user_alerts(
    *,
    user_id: str,
    research_objects: Mapping[str, Any] | list[Any] | None = None,
) -> dict[str, Any]:
    """Evaluate every active alert rule for one user. Returns per-rule
    results plus any newly-created notifications. Never fabricates a
    triggered/not-triggered verdict when the underlying signal is missing —
    reports ``unavailable`` instead (see ``workflow_automation.evaluation``).
    """
    service = get_workflow_automation_service()
    rules = service.list_alert_rules(user_id=user_id, active_only=True)

    valuation_cache: dict[str, dict[str, str]] = {}
    results: list[dict[str, Any]] = []
    new_notifications: list[dict[str, Any]] = []

    for rule in rules:
        rule_type = rule["rule_type"]
        symbol = rule.get("symbol")
        params = rule.get("params") or {}

        if rule_type in ("price_above", "price_below"):
            direction = "above" if rule_type == "price_above" else "below"
            threshold = params.get("threshold_price")
            if symbol and isinstance(threshold, (int, float)):
                evaluation = evaluate_price_alert(
                    direction=direction,
                    threshold_price=float(threshold),
                    current_price=_current_price(symbol),
                    symbol=symbol,
                )
            else:
                evaluation = AlertEvaluation(
                    status=AlertStatus.UNAVAILABLE,
                    message="Data unavailable. Rule is missing symbol/threshold_price.",
                )
        elif rule_type == "valuation_flip":
            portfolio_id = rule.get("portfolio_id")
            watch_class = params.get("watch_class", "overvalued")
            if portfolio_id and symbol:
                if portfolio_id not in valuation_cache:
                    valuation_cache[portfolio_id] = _valuation_classes_for_portfolio(
                        portfolio_id, user_id=user_id, research_objects=research_objects
                    )
                current_class = valuation_cache[portfolio_id].get(symbol)
                evaluation = evaluate_valuation_alert(
                    watch_class=watch_class, current_class=current_class, symbol=symbol
                )
            else:
                evaluation = AlertEvaluation(
                    status=AlertStatus.UNAVAILABLE,
                    message="Data unavailable. Rule is missing symbol/portfolio_id.",
                )
        elif rule_type == "research_stale":
            evaluation = evaluate_research_stale_alert(
                last_analysed_at=params.get("last_analysed_at"),
                max_age_days=int(params.get("max_age_days", 90)),
                symbol=symbol or "?",
            )
        else:  # earnings_upcoming
            evaluation = evaluate_earnings_alert(symbol=symbol or "?")

        service.record_alert_evaluation(
            rule["rule_id"], user_id=user_id, status=evaluation.status.value
        )
        notification = _maybe_notify(user_id=user_id, rule=rule, evaluation=evaluation)
        if notification is not None:
            new_notifications.append(notification)

        results.append(
            {
                "rule_id": rule["rule_id"],
                "rule_type": rule_type,
                "symbol": symbol,
                **evaluation.to_dict(),
            }
        )

    return {
        "available": True,
        "message": None,
        "evaluated_count": len(results),
        "triggered_count": sum(1 for r in results if r["status"] == "triggered"),
        "results": results,
        "new_notifications": new_notifications,
    }


# ----------------------------------------------------------- scheduled runs
def _serialize_report(payload: dict[str, Any], *, format: str) -> str:
    """Pure formatting only — never a new export engine."""
    if format == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["symbol", "weight", "valuation_class", "margin_of_safety"])
        heatmap_rows = ((payload.get("valuation_heatmap") or {}).get("rows")) or []
        for row in heatmap_rows:
            writer.writerow(
                [
                    row.get("symbol"),
                    row.get("weight"),
                    row.get("valuation_class"),
                    row.get("margin_of_safety"),
                ]
            )
        return buffer.getvalue()
    return json.dumps(payload, indent=2, default=str)


def run_scheduled_report_now(
    schedule_id: str,
    *,
    user_id: str,
    research_objects: Mapping[str, Any] | list[Any] | None = None,
) -> dict[str, Any]:
    """Manually run a Scheduled Report definition immediately.

    This is the **only** implemented execution path — see package README
    "no autonomous scheduler" for why. Reuses the Portfolio Intelligence
    Engine (which itself reuses Portfolio Analytics) to build the snapshot,
    then serializes it — no new export engine.
    """
    from dsp_platform.portfolio_intelligence_engine import (
        evaluate_portfolio_intelligence_engine,
    )
    from dsp_platform.portfolio_store_facade import list_portfolio_holdings

    service = get_workflow_automation_service()
    schedule = service.get_scheduled_report(schedule_id, user_id=user_id)

    try:
        holdings = list_portfolio_holdings(schedule["portfolio_id"], user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        return {
            "available": False,
            "message": "Data unavailable.",
            "error": str(exc),
        }

    portfolio = {
        "holdings": [
            {"symbol": h["symbol"], "weight": h["weight"], "sector": h.get("sector")}
            for h in holdings
        ]
    }
    result = evaluate_portfolio_intelligence_engine(
        portfolio, research_objects=research_objects
    )
    content = _serialize_report(result, format=schedule["format"])
    service.record_schedule_run(schedule_id, user_id=user_id)

    return {
        "available": True,
        "message": None,
        "schedule_id": schedule_id,
        "format": schedule["format"],
        "content": content,
    }


def workflow_automation_health() -> dict[str, Any]:
    return {
        "service_version": WORKFLOW_AUTOMATION_SERVICE_VERSION,
        "schema": workflow_automation_schema(),
    }


def reset_workflow_automation_for_tests(service: Any | None = None) -> None:
    _reset_service(service)
