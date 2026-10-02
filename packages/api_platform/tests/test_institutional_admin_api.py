"""EPIC-A010 institutional admin API smoke tests (P0-05 always-on admin gate)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from admin import AdminService, reset_admin_service_for_tests
from api_platform.api.app import create_app
from auth import (
    AuthService,
    RoleRegistry,
    reset_auth_service_for_tests,
    reset_role_registry_for_tests,
)
from auth_test_helpers import admin_headers, bearer_headers, register_user
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
    get_persistence_service,
    reset_persistence_service_for_tests,
    reset_repository_registry_for_tests,
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
    reset_admin_service_for_tests(AdminService(ps, auth))
    app = create_app(enable_security=False)
    with TestClient(app) as c:
        yield c
    reset_admin_service_for_tests(None)
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


@pytest.fixture()
def headers(client: TestClient) -> dict[str, str]:
    return admin_headers(client, user_id="u-adminops", username="adminops")


def test_admin_schema_dashboard_health_metrics(
    client: TestClient, headers: dict[str, str]
) -> None:
    client.cookies.clear()
    assert client.get("/api/v1/admin/schema").status_code == 401

    schema = client.get("/api/v1/admin/schema", headers=headers)
    assert schema.status_code == 200
    assert schema.json()["ok"] is True

    dash = client.get(
        "/api/v1/admin/dashboard",
        headers=headers,
        params={"generated_at": FIXED},
    )
    assert dash.status_code == 200
    assert dash.json()["result"]["generated_at"] == FIXED

    health = client.get("/api/v1/admin/health", headers=headers)
    assert health.status_code == 200
    assert health.json()["result"]["ready"] is True

    metrics = client.get("/api/v1/admin/metrics", headers=headers)
    assert metrics.status_code == 200
    assert "users" in metrics.json()["result"]


def test_admin_users_audit_search_export(
    client: TestClient, headers: dict[str, str]
) -> None:
    created = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={
            "username": "console1",
            "email": "c1@example.com",
            "password": "StrongPass12!",
            "roles": ["read_only"],
            "user_id": "u-c1",
            "created_at": FIXED,
            "password_salt": "aabbccddeeff0011",
        },
    )
    assert created.status_code == 200

    users = client.get("/api/v1/admin/users", headers=headers)
    assert users.status_code == 200
    assert any(u["user_id"] == "u-c1" for u in users.json()["result"])

    get_persistence_service().persist_audit_record(
        {
            "event_id": "api-1",
            "event_type": "note",
            "subject": "INFY",
            "created_at": FIXED,
            "message": "ops note",
        },
        created_at=FIXED,
    )

    audit = client.get(
        "/api/v1/admin/audit",
        headers=headers,
        params={"subject": "INFY"},
    )
    assert audit.status_code == 200
    assert len(audit.json()["result"]) == 1

    search = client.post(
        "/api/v1/admin/search",
        headers=headers,
        json={"query": "ops note", "scope": "audit"},
    )
    assert search.status_code == 200
    assert search.json()["result"]["count"] == 1

    export = client.get("/api/v1/admin/audit/export", headers=headers)
    assert export.status_code == 200
    assert export.json()["result"]["count"] == 1

    roles = client.get("/api/v1/admin/roles", headers=headers)
    assert roles.status_code == 200
    versions = client.get("/api/v1/admin/versions", headers=headers)
    assert versions.status_code == 200
    flags = client.get("/api/v1/admin/feature-flags", headers=headers)
    assert flags.status_code == 200


def test_admin_requires_bearer_always(client: TestClient) -> None:
    """P0-05 — admin gate is always enforced (not opt-in)."""
    denied = client.get("/api/v1/admin/users")
    assert denied.status_code == 401

    register_user(
        client,
        user_id="u-adminops2",
        username="adminops2",
        roles=["administrator"],
    )
    token_headers = bearer_headers(client, username="adminops2")
    allowed = client.get("/api/v1/admin/users", headers=token_headers)
    assert allowed.status_code == 200

    # Header spoof without Bearer/cookie fails.
    client.cookies.clear()
    assert (
        client.get(
            "/api/v1/admin/users",
            headers={"X-User-Id": "u-adminops2"},
        ).status_code
        == 401
    )


def test_admin_api_rejects_non_admin_and_searches_real_users(client: TestClient) -> None:
    """Authorization is the token's permissions, not a client-supplied role flag."""
    register_user(
        client,
        user_id="u-analyst-gate",
        username="analystgate",
        email="analyst.gate@example.com",
        roles=["research_analyst"],
    )
    register_user(
        client,
        user_id="u-admin-gate",
        username="admingate",
        roles=["administrator"],
    )
    analyst = bearer_headers(client, username="analystgate")
    assert client.get("/api/v1/admin/users", headers=analyst).status_code == 403
    assert (
        client.post(
            "/api/v1/admin/search",
            headers=analyst,
            json={"query": "analyst.gate", "scope": "users"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/auth/enterprise/admin/users/u-analyst-gate/status",
            headers=analyst,
            json={"active": False},
        ).status_code
        == 403
    )

    admin = bearer_headers(client, username="admingate")
    listed = client.get("/api/v1/admin/users", headers=admin)
    assert listed.status_code == 200
    emails = [row.get("email") for row in listed.json()["result"]]
    assert "analyst.gate@example.com" in emails

    found = client.post(
        "/api/v1/admin/search",
        headers=admin,
        json={"query": "analyst.gate@example.com", "scope": "users"},
    )
    assert found.status_code == 200
    body = found.json()["result"]
    assert body["scope"] == "users"
    assert any(
        row.get("email") == "analyst.gate@example.com" for row in body["results"]
    )

    updated = client.post(
        "/api/v1/auth/enterprise/admin/users/u-analyst-gate/status",
        headers=admin,
        json={"active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["result"]["status"] == "disabled"

    again = client.get("/api/v1/admin/users/u-analyst-gate", headers=admin)
    assert again.status_code == 200
    assert again.json()["result"]["status"] == "disabled"
