"""Tests for workflow_automation.service — ownership-checked CRUD."""

from __future__ import annotations

import pytest

from workflow_automation import ForbiddenError, NotFoundError, ValidationError
from workflow_automation.service import WorkflowAutomationService


@pytest.fixture
def svc() -> WorkflowAutomationService:
    return WorkflowAutomationService()


class TestSchema:
    def test_schema_lists_rule_types_and_frequencies(
        self, svc: WorkflowAutomationService
    ) -> None:
        schema = svc.schema()
        assert "price_above" in schema["alert_rule_types"]
        assert "earnings_upcoming" in schema["alert_rule_types"]
        assert "weekly" in schema["schedule_frequencies"]


class TestAlertRuleCrud:
    def test_create_and_get(self, svc: WorkflowAutomationService) -> None:
        rule = svc.create_alert_rule(
            user_id="u1",
            rule_type="price_above",
            symbol="AAPL",
            params={"threshold_price": 200.0},
        )
        fetched = svc.get_alert_rule(rule["rule_id"], user_id="u1")
        assert fetched["symbol"] == "AAPL"
        assert fetched["active"] is True

    def test_create_rejects_invalid_rule_type(
        self, svc: WorkflowAutomationService
    ) -> None:
        with pytest.raises(ValidationError):
            svc.create_alert_rule(user_id="u1", rule_type="not_a_type", symbol="AAPL")

    def test_create_rejects_missing_symbol(
        self, svc: WorkflowAutomationService
    ) -> None:
        with pytest.raises(ValidationError):
            svc.create_alert_rule(user_id="u1", rule_type="price_above")

    def test_list_scoped_to_user(self, svc: WorkflowAutomationService) -> None:
        svc.create_alert_rule(user_id="u1", rule_type="price_above", symbol="AAPL")
        svc.create_alert_rule(user_id="u2", rule_type="price_above", symbol="MSFT")
        rows = svc.list_alert_rules(user_id="u1")
        assert len(rows) == 1
        assert rows[0]["symbol"] == "AAPL"

    def test_list_active_only_filter(self, svc: WorkflowAutomationService) -> None:
        rule = svc.create_alert_rule(
            user_id="u1", rule_type="price_above", symbol="AAPL"
        )
        svc.update_alert_rule(rule["rule_id"], user_id="u1", active=False)
        assert svc.list_alert_rules(user_id="u1", active_only=True) == []
        assert len(svc.list_alert_rules(user_id="u1")) == 1

    def test_get_raises_not_found(self, svc: WorkflowAutomationService) -> None:
        with pytest.raises(NotFoundError):
            svc.get_alert_rule("missing", user_id="u1")

    def test_get_raises_forbidden_for_other_user(
        self, svc: WorkflowAutomationService
    ) -> None:
        rule = svc.create_alert_rule(
            user_id="u1", rule_type="price_above", symbol="AAPL"
        )
        with pytest.raises(ForbiddenError):
            svc.get_alert_rule(rule["rule_id"], user_id="u2")

    def test_update_alert_rule_params(self, svc: WorkflowAutomationService) -> None:
        rule = svc.create_alert_rule(
            user_id="u1",
            rule_type="price_above",
            symbol="AAPL",
            params={"threshold_price": 100},
        )
        updated = svc.update_alert_rule(
            rule["rule_id"], user_id="u1", params={"threshold_price": 250}
        )
        assert updated["params"]["threshold_price"] == 250

    def test_record_alert_evaluation(self, svc: WorkflowAutomationService) -> None:
        rule = svc.create_alert_rule(
            user_id="u1", rule_type="price_above", symbol="AAPL"
        )
        updated = svc.record_alert_evaluation(
            rule["rule_id"], user_id="u1", status="triggered"
        )
        assert updated["last_status"] == "triggered"
        assert updated["last_evaluated_at"] is not None

    def test_delete_alert_rule(self, svc: WorkflowAutomationService) -> None:
        rule = svc.create_alert_rule(
            user_id="u1", rule_type="price_above", symbol="AAPL"
        )
        assert svc.delete_alert_rule(rule["rule_id"], user_id="u1") is True
        with pytest.raises(NotFoundError):
            svc.get_alert_rule(rule["rule_id"], user_id="u1")

    def test_delete_raises_forbidden_for_other_user(
        self, svc: WorkflowAutomationService
    ) -> None:
        rule = svc.create_alert_rule(
            user_id="u1", rule_type="price_above", symbol="AAPL"
        )
        with pytest.raises(ForbiddenError):
            svc.delete_alert_rule(rule["rule_id"], user_id="u2")


class TestScheduledReportCrud:
    def test_create_and_get(self, svc: WorkflowAutomationService) -> None:
        schedule = svc.create_scheduled_report(
            user_id="u1", portfolio_id="pf_1", frequency="weekly", format="csv"
        )
        fetched = svc.get_scheduled_report(schedule["schedule_id"], user_id="u1")
        assert fetched["frequency"] == "weekly"
        assert fetched["format"] == "csv"

    def test_create_rejects_invalid_frequency(
        self, svc: WorkflowAutomationService
    ) -> None:
        with pytest.raises(ValidationError):
            svc.create_scheduled_report(
                user_id="u1", portfolio_id="pf_1", frequency="hourly"
            )

    def test_create_rejects_invalid_format(
        self, svc: WorkflowAutomationService
    ) -> None:
        with pytest.raises(ValidationError):
            svc.create_scheduled_report(
                user_id="u1", portfolio_id="pf_1", frequency="daily", format="pdf"
            )

    def test_list_scoped_to_user(self, svc: WorkflowAutomationService) -> None:
        svc.create_scheduled_report(
            user_id="u1", portfolio_id="pf_1", frequency="daily"
        )
        svc.create_scheduled_report(
            user_id="u2", portfolio_id="pf_2", frequency="weekly"
        )
        rows = svc.list_scheduled_reports(user_id="u1")
        assert len(rows) == 1

    def test_update_scheduled_report(self, svc: WorkflowAutomationService) -> None:
        schedule = svc.create_scheduled_report(
            user_id="u1", portfolio_id="pf_1", frequency="daily"
        )
        updated = svc.update_scheduled_report(
            schedule["schedule_id"], user_id="u1", frequency="monthly", active=False
        )
        assert updated["frequency"] == "monthly"
        assert updated["active"] is False

    def test_record_schedule_run(self, svc: WorkflowAutomationService) -> None:
        schedule = svc.create_scheduled_report(
            user_id="u1", portfolio_id="pf_1", frequency="daily"
        )
        updated = svc.record_schedule_run(schedule["schedule_id"], user_id="u1")
        assert updated["last_run_at"] is not None

    def test_delete_scheduled_report(self, svc: WorkflowAutomationService) -> None:
        schedule = svc.create_scheduled_report(
            user_id="u1", portfolio_id="pf_1", frequency="daily"
        )
        assert (
            svc.delete_scheduled_report(schedule["schedule_id"], user_id="u1") is True
        )
        with pytest.raises(NotFoundError):
            svc.get_scheduled_report(schedule["schedule_id"], user_id="u1")


class TestNotifications:
    def test_create_and_list(self, svc: WorkflowAutomationService) -> None:
        svc.create_notification(
            user_id="u1", kind="alert", title="Price alert", message="AAPL hit $200"
        )
        rows = svc.list_notifications(user_id="u1")
        assert len(rows) == 1
        assert rows[0]["title"] == "Price alert"
        assert rows[0]["read_at"] is None

    def test_list_scoped_to_user(self, svc: WorkflowAutomationService) -> None:
        svc.create_notification(user_id="u1", kind="alert", title="A", message="a")
        svc.create_notification(user_id="u2", kind="alert", title="B", message="b")
        assert len(svc.list_notifications(user_id="u1")) == 1

    def test_unread_only_filter(self, svc: WorkflowAutomationService) -> None:
        n = svc.create_notification(user_id="u1", kind="alert", title="A", message="a")
        svc.create_notification(user_id="u1", kind="alert", title="B", message="b")
        svc.mark_notification_read(n["notification_id"], user_id="u1")
        unread = svc.list_notifications(user_id="u1", unread_only=True)
        assert len(unread) == 1
        assert unread[0]["title"] == "B"

    def test_mark_read_raises_forbidden_for_other_user(
        self, svc: WorkflowAutomationService
    ) -> None:
        n = svc.create_notification(user_id="u1", kind="alert", title="A", message="a")
        with pytest.raises(ForbiddenError):
            svc.mark_notification_read(n["notification_id"], user_id="u2")

    def test_mark_read_raises_not_found(self, svc: WorkflowAutomationService) -> None:
        with pytest.raises(NotFoundError):
            svc.mark_notification_read("missing", user_id="u1")
