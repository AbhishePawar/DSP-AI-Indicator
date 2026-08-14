"""Durability tests for workflow_automation.db_store.DatabaseWorkflowAutomationStore.

Mirrors packages/portfolio_store/tests/test_db_store.py's rehydrate-after-
restart pattern exactly.
"""

from __future__ import annotations

from production_platform import InMemoryDatabasePort
from workflow_automation.db_store import (
    DatabaseWorkflowAutomationStore,
    build_workflow_automation_store,
)
from workflow_automation.service import WorkflowAutomationService
from workflow_automation.store import InMemoryWorkflowAutomationStore


class TestBuildWorkflowAutomationStore:
    def test_returns_in_memory_when_no_database(self) -> None:
        store = build_workflow_automation_store()
        assert isinstance(store, InMemoryWorkflowAutomationStore)
        assert not isinstance(store, DatabaseWorkflowAutomationStore)

    def test_returns_database_backed_when_database_supplied(self) -> None:
        db = InMemoryDatabasePort()
        store = build_workflow_automation_store(db)
        assert isinstance(store, DatabaseWorkflowAutomationStore)


class TestDatabaseWorkflowAutomationStoreDurability:
    def test_survives_rehydrate_across_service_instances(self) -> None:
        db = InMemoryDatabasePort()
        svc = WorkflowAutomationService(store=DatabaseWorkflowAutomationStore(db))
        rule = svc.create_alert_rule(
            user_id="u1",
            rule_type="price_above",
            symbol="AAPL",
            params={"threshold_price": 200.0},
        )
        schedule = svc.create_scheduled_report(
            user_id="u1", portfolio_id="pf_1", frequency="weekly", format="csv"
        )
        notification = svc.create_notification(
            user_id="u1", kind="alert", title="Test", message="hello"
        )

        # New service instance, same underlying DatabasePort — simulates a
        # process restart with the same durable backend.
        reloaded = WorkflowAutomationService(store=DatabaseWorkflowAutomationStore(db))

        restored_rule = reloaded.get_alert_rule(rule["rule_id"], user_id="u1")
        assert restored_rule["symbol"] == "AAPL"
        assert restored_rule["params"]["threshold_price"] == 200.0

        restored_schedule = reloaded.get_scheduled_report(
            schedule["schedule_id"], user_id="u1"
        )
        assert restored_schedule["frequency"] == "weekly"

        notifications = reloaded.list_notifications(user_id="u1")
        assert len(notifications) == 1
        assert notifications[0]["notification_id"] == notification["notification_id"]
        assert notifications[0]["read_at"] is None

    def test_notification_read_state_persists_across_restart(self) -> None:
        db = InMemoryDatabasePort()
        svc = WorkflowAutomationService(store=DatabaseWorkflowAutomationStore(db))
        notification = svc.create_notification(
            user_id="u1", kind="alert", title="Test", message="hello"
        )
        svc.mark_notification_read(notification["notification_id"], user_id="u1")

        reloaded = WorkflowAutomationService(store=DatabaseWorkflowAutomationStore(db))
        restored = reloaded.list_notifications(user_id="u1")
        assert restored[0]["read_at"] is not None

    def test_delete_alert_rule_persists_across_restart(self) -> None:
        db = InMemoryDatabasePort()
        svc = WorkflowAutomationService(store=DatabaseWorkflowAutomationStore(db))
        rule = svc.create_alert_rule(
            user_id="u1", rule_type="price_above", symbol="AAPL"
        )
        svc.delete_alert_rule(rule["rule_id"], user_id="u1")

        reloaded = WorkflowAutomationService(store=DatabaseWorkflowAutomationStore(db))
        assert reloaded.list_alert_rules(user_id="u1") == []
