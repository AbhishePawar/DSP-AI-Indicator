"""Tests for dsp_platform.workflow_automation — orchestration façade.

Verifies the façade correctly wires ``workflow_automation`` (persistence,
pure evaluation) with already-tested engine outputs
(``market_quotes``, ``portfolio_store_facade``, ``portfolio_intelligence_engine``)
via mocking at those exact boundaries — never re-derives a price/valuation
number itself. Also verifies ``DSPPlatform`` delegation.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from dsp_platform import PlatformBuilder, PlatformConfiguration
from dsp_platform.portfolio_store_facade import reset_portfolio_store_for_tests
from dsp_platform.workflow_automation import (
    create_alert_rule,
    create_scheduled_report,
    delete_alert_rule,
    evaluate_user_alerts,
    get_alert_rule,
    list_alert_rules,
    list_notifications,
    list_scheduled_reports,
    mark_notification_read,
    reset_workflow_automation_for_tests,
    run_scheduled_report_now,
    update_alert_rule,
    workflow_automation_health,
    workflow_automation_schema,
)
from portfolio_store import PortfolioService
from workflow_automation import WorkflowAutomationService


@pytest.fixture(autouse=True)
def _fresh_stores():
    reset_workflow_automation_for_tests(WorkflowAutomationService())
    reset_portfolio_store_for_tests(PortfolioService())
    yield
    reset_workflow_automation_for_tests(None)
    reset_portfolio_store_for_tests(None)


@pytest.fixture
def platform():
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .build()
    )


class TestSchemaAndHealth:
    def test_schema_lists_rule_types(self) -> None:
        schema = workflow_automation_schema()
        assert "price_above" in schema["alert_rule_types"]

    def test_health_reports_version(self) -> None:
        health = workflow_automation_health()
        assert health["service_version"]


class TestAlertRuleCrud:
    def test_create_list_update_delete(self) -> None:
        rule = create_alert_rule(
            user_id="u1",
            rule_type="price_above",
            symbol="AAPL",
            params={"threshold_price": 200},
        )
        assert len(list_alert_rules(user_id="u1")) == 1
        updated = update_alert_rule(rule["rule_id"], user_id="u1", active=False)
        assert updated["active"] is False
        assert delete_alert_rule(rule["rule_id"], user_id="u1") is True
        assert list_alert_rules(user_id="u1") == []

    def test_get_alert_rule(self) -> None:
        rule = create_alert_rule(user_id="u1", rule_type="price_above", symbol="AAPL")
        fetched = get_alert_rule(rule["rule_id"], user_id="u1")
        assert fetched["symbol"] == "AAPL"


class TestEvaluateUserAlertsPrice:
    def test_price_alert_triggers_using_reused_market_quote(self) -> None:
        create_alert_rule(
            user_id="u1",
            rule_type="price_above",
            symbol="AAPL",
            params={"threshold_price": 100.0},
        )
        with patch(
            "dsp_platform.workflow_automation.service._current_price",
            return_value=150.0,
        ):
            result = evaluate_user_alerts(user_id="u1")
        assert result["triggered_count"] == 1
        assert result["results"][0]["status"] == "triggered"
        assert len(result["new_notifications"]) == 1

    def test_price_alert_unavailable_without_quote(self) -> None:
        create_alert_rule(
            user_id="u1",
            rule_type="price_above",
            symbol="AAPL",
            params={"threshold_price": 100.0},
        )
        with patch(
            "dsp_platform.workflow_automation.service._current_price", return_value=None
        ):
            result = evaluate_user_alerts(user_id="u1")
        assert result["results"][0]["status"] == "unavailable"
        assert result["new_notifications"] == []

    def test_no_duplicate_notification_on_repeat_trigger(self) -> None:
        create_alert_rule(
            user_id="u1",
            rule_type="price_above",
            symbol="AAPL",
            params={"threshold_price": 100.0},
        )
        with patch(
            "dsp_platform.workflow_automation.service._current_price",
            return_value=150.0,
        ):
            first = evaluate_user_alerts(user_id="u1")
            second = evaluate_user_alerts(user_id="u1")
        assert len(first["new_notifications"]) == 1
        assert len(second["new_notifications"]) == 0
        assert len(list_notifications(user_id="u1")) == 1


class TestEvaluateUserAlertsValuation:
    def test_valuation_flip_triggers_using_reused_engine(self) -> None:
        portfolio = create_alert_rule  # placeholder to avoid unused import lint
        del portfolio
        from dsp_platform.portfolio_store_facade import (
            create_portfolio,
            upsert_portfolio_holding,
        )

        pf = create_portfolio(user_id="u1", name="P1")
        upsert_portfolio_holding(
            pf["portfolio_id"], user_id="u1", symbol="AAPL", weight=1.0
        )
        create_alert_rule(
            user_id="u1",
            rule_type="valuation_flip",
            symbol="AAPL",
            portfolio_id=pf["portfolio_id"],
            params={"watch_class": "overvalued"},
        )
        with patch(
            "dsp_platform.portfolio_intelligence_engine.evaluate_portfolio_intelligence_engine",
            return_value={
                "available": True,
                "valuation_heatmap": {
                    "rows": [{"symbol": "AAPL", "valuation_class": "overvalued"}]
                },
            },
        ):
            result = evaluate_user_alerts(user_id="u1")
        assert result["results"][0]["status"] == "triggered"


class TestEvaluateUserAlertsResearchStale:
    def test_triggers_when_stale(self) -> None:
        create_alert_rule(
            user_id="u1",
            rule_type="research_stale",
            symbol="AAPL",
            params={"last_analysed_at": "2000-01-01", "max_age_days": 30},
        )
        result = evaluate_user_alerts(user_id="u1")
        assert result["results"][0]["status"] == "triggered"


class TestEvaluateUserAlertsEarnings:
    def test_always_unavailable(self) -> None:
        create_alert_rule(user_id="u1", rule_type="earnings_upcoming", symbol="AAPL")
        result = evaluate_user_alerts(user_id="u1")
        assert result["results"][0]["status"] == "unavailable"
        assert "Data unavailable" in result["results"][0]["message"]


class TestNotifications:
    def test_mark_read(self) -> None:
        create_alert_rule(
            user_id="u1",
            rule_type="price_above",
            symbol="AAPL",
            params={"threshold_price": 1.0},
        )
        with patch(
            "dsp_platform.workflow_automation.service._current_price", return_value=10.0
        ):
            evaluate_user_alerts(user_id="u1")
        notifications = list_notifications(user_id="u1")
        assert len(notifications) == 1
        updated = mark_notification_read(
            notifications[0]["notification_id"], user_id="u1"
        )
        assert updated["read_at"] is not None
        assert list_notifications(user_id="u1", unread_only=True) == []


class TestScheduledReports:
    def test_create_list_and_run_now(self) -> None:
        from dsp_platform.portfolio_store_facade import (
            create_portfolio,
            upsert_portfolio_holding,
        )

        pf = create_portfolio(user_id="u1", name="P1")
        upsert_portfolio_holding(
            pf["portfolio_id"], user_id="u1", symbol="AAPL", weight=1.0
        )
        schedule = create_scheduled_report(
            user_id="u1",
            portfolio_id=pf["portfolio_id"],
            frequency="weekly",
            format="json",
        )
        assert len(list_scheduled_reports(user_id="u1")) == 1
        with patch(
            "dsp_platform.portfolio_intelligence_engine.evaluate_portfolio_intelligence_engine",
            return_value={"available": True, "valuation_heatmap": {"rows": []}},
        ):
            run = run_scheduled_report_now(schedule["schedule_id"], user_id="u1")
        assert run["available"] is True
        assert "valuation_heatmap" in run["content"]

    def test_run_now_csv_format(self) -> None:
        from dsp_platform.portfolio_store_facade import (
            create_portfolio,
            upsert_portfolio_holding,
        )

        pf = create_portfolio(user_id="u1", name="P1")
        upsert_portfolio_holding(
            pf["portfolio_id"], user_id="u1", symbol="AAPL", weight=1.0
        )
        schedule = create_scheduled_report(
            user_id="u1",
            portfolio_id=pf["portfolio_id"],
            frequency="daily",
            format="csv",
        )
        with patch(
            "dsp_platform.portfolio_intelligence_engine.evaluate_portfolio_intelligence_engine",
            return_value={
                "available": True,
                "valuation_heatmap": {
                    "rows": [
                        {
                            "symbol": "AAPL",
                            "weight": 1.0,
                            "valuation_class": "undervalued",
                            "margin_of_safety": 0.2,
                        }
                    ]
                },
            },
        ):
            run = run_scheduled_report_now(schedule["schedule_id"], user_id="u1")
        assert "AAPL" in run["content"]
        assert "undervalued" in run["content"]


class TestDspPlatformDelegation:
    def test_platform_create_and_list_alert_rules(self, platform) -> None:
        platform.create_alert_rule(user_id="u1", rule_type="price_above", symbol="AAPL")
        assert len(platform.list_alert_rules(user_id="u1")) == 1

    def test_platform_evaluate_user_alerts(self, platform) -> None:
        platform.create_alert_rule(
            user_id="u1", rule_type="earnings_upcoming", symbol="AAPL"
        )
        result = platform.evaluate_user_alerts(user_id="u1")
        assert result["evaluated_count"] == 1

    def test_platform_scheduled_report_crud(self, platform) -> None:
        schedule = platform.create_scheduled_report(
            user_id="u1", portfolio_id="pf_1", frequency="daily"
        )
        assert len(platform.list_scheduled_reports(user_id="u1")) == 1
        assert (
            platform.delete_scheduled_report(schedule["schedule_id"], user_id="u1")
            is True
        )

    def test_platform_workflow_automation_health(self, platform) -> None:
        health = platform.workflow_automation_health()
        assert health["service_version"]
