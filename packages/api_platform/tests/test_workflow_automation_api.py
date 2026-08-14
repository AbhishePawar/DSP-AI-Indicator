"""Workflow Automation API tests (RC1 Milestone 5) — CRUD, ownership, evaluation."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api_platform.api.app import create_app
from auth import (
    AuthService,
    RoleRegistry,
    reset_auth_service_for_tests,
    reset_role_registry_for_tests,
)
from dsp_platform.portfolio_store_facade import reset_portfolio_store_for_tests
from dsp_platform.workflow_automation import reset_workflow_automation_for_tests
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
    reset_persistence_service_for_tests,
    reset_repository_registry_for_tests,
)
from portfolio_store import InMemoryPortfolioStore, PortfolioService
from workflow_automation import (
    InMemoryWorkflowAutomationStore,
    WorkflowAutomationService,
)

FIXED = datetime.now(UTC).replace(microsecond=0).isoformat()


@pytest.fixture()
def client() -> TestClient:
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    auth = AuthService(ps, jwt_secret="test-secret")
    reset_auth_service_for_tests(auth)
    reset_portfolio_store_for_tests(PortfolioService(store=InMemoryPortfolioStore()))
    reset_workflow_automation_for_tests(
        WorkflowAutomationService(store=InMemoryWorkflowAutomationStore())
    )
    app = create_app(enable_security=False)
    with TestClient(app) as c:
        yield c
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)
    reset_portfolio_store_for_tests(None)
    reset_workflow_automation_for_tests(None)


def _register_and_login(client: TestClient, *, username: str, user_id: str) -> str:
    client.cookies.clear()
    created = client.post(
        "/api/v1/auth/rbac/users",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "StrongPass12!",
            "user_id": user_id,
            "created_at": FIXED,
            "password_salt": "aabbccddeeff0011",
        },
    )
    assert created.status_code == 200, created.text
    login = client.post(
        "/api/v1/auth/rbac/login",
        json={
            "username": username,
            "password": "StrongPass12!",
            "created_at": FIXED,
            "session_id": f"s-{user_id}",
            "access_jti": f"a-{user_id}",
            "refresh_jti": f"r-{user_id}",
        },
    )
    assert login.status_code == 200, login.text
    return login.json()["result"]["tokens"]["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestAuthenticationRequired:
    def test_list_alert_rules_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/workflow-automation/alerts")
        assert response.status_code == 401

    def test_create_alert_rule_requires_auth(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/workflow-automation/alerts",
            json={"rule_type": "price_above", "symbol": "AAPL"},
        )
        assert response.status_code == 401


class TestSchemaAndHealth:
    def test_schema_endpoint_public(self, client: TestClient) -> None:
        response = client.get("/api/v1/workflow-automation/schema")
        assert response.status_code == 200
        assert "price_above" in response.json()["schema"]["alert_rule_types"]

    def test_health_endpoint_public(self, client: TestClient) -> None:
        response = client.get("/api/v1/workflow-automation/health")
        assert response.status_code == 200
        assert response.json()["health"]["service_version"]


class TestAlertRuleCrud:
    def test_create_list_get_update_delete(self, client: TestClient) -> None:
        token = _register_and_login(client, username="analyst1", user_id="u-analyst1")
        headers = _auth_headers(token)

        created = client.post(
            "/api/v1/workflow-automation/alerts",
            json={
                "rule_type": "price_above",
                "symbol": "AAPL",
                "params": {"threshold_price": 200.0},
            },
            headers=headers,
        )
        assert created.status_code == 200
        rule = created.json()["rule"]
        rid = rule["rule_id"]

        listed = client.get("/api/v1/workflow-automation/alerts", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()["rules"]) == 1

        fetched = client.get(
            f"/api/v1/workflow-automation/alerts/{rid}", headers=headers
        )
        assert fetched.status_code == 200
        assert fetched.json()["rule"]["symbol"] == "AAPL"

        updated = client.put(
            f"/api/v1/workflow-automation/alerts/{rid}",
            json={"active": False},
            headers=headers,
        )
        assert updated.status_code == 200
        assert updated.json()["rule"]["active"] is False

        deleted = client.delete(
            f"/api/v1/workflow-automation/alerts/{rid}", headers=headers
        )
        assert deleted.status_code == 200

        missing = client.get(
            f"/api/v1/workflow-automation/alerts/{rid}", headers=headers
        )
        assert missing.status_code == 404

    def test_ownership_enforced_403(self, client: TestClient) -> None:
        token1 = _register_and_login(client, username="analyst1", user_id="u-1")
        token2 = _register_and_login(client, username="analyst2", user_id="u-2")
        created = client.post(
            "/api/v1/workflow-automation/alerts",
            json={"rule_type": "price_above", "symbol": "AAPL"},
            headers=_auth_headers(token1),
        )
        rid = created.json()["rule"]["rule_id"]
        response = client.get(
            f"/api/v1/workflow-automation/alerts/{rid}", headers=_auth_headers(token2)
        )
        assert response.status_code == 403

    def test_create_rejects_invalid_rule_type(self, client: TestClient) -> None:
        token = _register_and_login(client, username="analyst1", user_id="u-1")
        response = client.post(
            "/api/v1/workflow-automation/alerts",
            json={"rule_type": "not_a_type", "symbol": "AAPL"},
            headers=_auth_headers(token),
        )
        assert response.status_code == 400


class TestEvaluateAlerts:
    def test_evaluate_reports_unavailable_without_quote(
        self, client: TestClient
    ) -> None:
        token = _register_and_login(client, username="analyst1", user_id="u-1")
        client.post(
            "/api/v1/workflow-automation/alerts",
            json={
                "rule_type": "price_above",
                "symbol": "AAPL",
                "params": {"threshold_price": 100.0},
            },
            headers=_auth_headers(token),
        )
        response = client.post(
            "/api/v1/workflow-automation/alerts/evaluate",
            json={},
            headers=_auth_headers(token),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["evaluated_count"] == 1
        assert body["results"][0]["status"] == "unavailable"

    def test_evaluate_triggers_and_creates_notification(
        self, client: TestClient
    ) -> None:
        token = _register_and_login(client, username="analyst1", user_id="u-1")
        client.post(
            "/api/v1/workflow-automation/alerts",
            json={
                "rule_type": "price_above",
                "symbol": "AAPL",
                "params": {"threshold_price": 100.0},
            },
            headers=_auth_headers(token),
        )
        with patch(
            "dsp_platform.workflow_automation.service._current_price",
            return_value=150.0,
        ):
            response = client.post(
                "/api/v1/workflow-automation/alerts/evaluate",
                json={},
                headers=_auth_headers(token),
            )
        assert response.status_code == 200
        body = response.json()
        assert body["triggered_count"] == 1
        assert len(body["new_notifications"]) == 1

        notifications = client.get(
            "/api/v1/workflow-automation/notifications", headers=_auth_headers(token)
        )
        assert notifications.status_code == 200
        assert len(notifications.json()["notifications"]) == 1


class TestNotifications:
    def test_mark_read(self, client: TestClient) -> None:
        token = _register_and_login(client, username="analyst1", user_id="u-1")
        client.post(
            "/api/v1/workflow-automation/alerts",
            json={
                "rule_type": "price_above",
                "symbol": "AAPL",
                "params": {"threshold_price": 1.0},
            },
            headers=_auth_headers(token),
        )
        with patch(
            "dsp_platform.workflow_automation.service._current_price", return_value=10.0
        ):
            client.post(
                "/api/v1/workflow-automation/alerts/evaluate",
                json={},
                headers=_auth_headers(token),
            )
        notifications = client.get(
            "/api/v1/workflow-automation/notifications", headers=_auth_headers(token)
        ).json()["notifications"]
        nid = notifications[0]["notification_id"]
        response = client.post(
            f"/api/v1/workflow-automation/notifications/{nid}/read",
            headers=_auth_headers(token),
        )
        assert response.status_code == 200
        assert response.json()["notification"]["read_at"] is not None


class TestScheduledReports:
    def test_create_list_get_update_delete(self, client: TestClient) -> None:
        token = _register_and_login(client, username="analyst1", user_id="u-1")
        headers = _auth_headers(token)
        portfolio = client.post(
            "/api/v1/portfolio", json={"name": "My Portfolio"}, headers=headers
        ).json()["result"]
        client.post(
            f"/api/v1/portfolio/{portfolio['portfolio_id']}/holdings",
            json={"symbol": "AAPL", "weight": 1.0},
            headers=headers,
        )

        created = client.post(
            "/api/v1/workflow-automation/schedules",
            json={
                "portfolio_id": portfolio["portfolio_id"],
                "frequency": "weekly",
                "format": "json",
            },
            headers=headers,
        )
        assert created.status_code == 200
        schedule = created.json()["schedule"]
        sid = schedule["schedule_id"]

        listed = client.get("/api/v1/workflow-automation/schedules", headers=headers)
        assert len(listed.json()["schedules"]) == 1

        run = client.post(
            f"/api/v1/workflow-automation/schedules/{sid}/run", json={}, headers=headers
        )
        assert run.status_code == 200
        assert run.json()["available"] is True

        updated = client.put(
            f"/api/v1/workflow-automation/schedules/{sid}",
            json={"frequency": "monthly"},
            headers=headers,
        )
        assert updated.json()["schedule"]["frequency"] == "monthly"

        deleted = client.delete(
            f"/api/v1/workflow-automation/schedules/{sid}", headers=headers
        )
        assert deleted.status_code == 200

    def test_create_rejects_invalid_frequency(self, client: TestClient) -> None:
        token = _register_and_login(client, username="analyst1", user_id="u-1")
        response = client.post(
            "/api/v1/workflow-automation/schedules",
            json={"portfolio_id": "pf_1", "frequency": "hourly"},
            headers=_auth_headers(token),
        )
        assert response.status_code == 400
