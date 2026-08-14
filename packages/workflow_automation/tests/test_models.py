"""Tests for workflow_automation.models."""

from __future__ import annotations

from workflow_automation.models import (
    AlertRule,
    Notification,
    ScheduledReport,
    freeze_mapping,
)


class TestAlertRule:
    def test_to_dict_roundtrip(self) -> None:
        rule = AlertRule(
            rule_id="alr_1",
            user_id="u1",
            rule_type="price_above",
            created_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-01T00:00:00+00:00",
            symbol="AAPL",
            params=freeze_mapping({"threshold_price": 200.0}),
        )
        data = rule.to_dict()
        assert data["symbol"] == "AAPL"
        assert data["params"] == {"threshold_price": 200.0}
        assert data["active"] is True


class TestScheduledReport:
    def test_to_dict_roundtrip(self) -> None:
        schedule = ScheduledReport(
            schedule_id="sch_1",
            user_id="u1",
            portfolio_id="pf_1",
            frequency="weekly",
            format="json",
            created_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-01T00:00:00+00:00",
            recipients=("a@example.com",),
        )
        data = schedule.to_dict()
        assert data["recipients"] == ["a@example.com"]
        assert data["last_run_at"] is None


class TestNotification:
    def test_to_dict_roundtrip(self) -> None:
        notification = Notification(
            notification_id="ntf_1",
            user_id="u1",
            kind="alert",
            title="Test",
            message="hello",
            created_at="2024-01-01T00:00:00+00:00",
        )
        data = notification.to_dict()
        assert data["title"] == "Test"
        assert data["read_at"] is None
