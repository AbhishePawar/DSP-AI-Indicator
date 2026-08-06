"""EPIC-A010 institutional admin API smoke tests."""

from __future__ import annotations

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
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
    get_persistence_service,
    reset_persistence_service_for_tests,
    reset_repository_registry_for_tests,
)

from datetime import UTC, datetime

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


def test_admin_schema_dashboard_health_metrics(client: TestClient) -> None:
    schema = client.get("/api/v1/admin/schema")
    assert schema.status_code == 200
    assert schema.json()["ok"] is True

    dash = client.get("/api/v1/admin/dashboard", params={"generated_at": FIXED})
    assert dash.status_code == 200
    assert dash.json()["result"]["generated_at"] == FIXED

    health = client.get("/api/v1/admin/health")
    assert health.status_code == 200
    assert health.json()["result"]["ready"] is True

    metrics = client.get("/api/v1/admin/metrics")
    assert metrics.status_code == 200
    assert "users" in metrics.json()["result"]


def test_admin_users_audit_search_export(client: TestClient) -> None:
    created = client.post(
        "/api/v1/admin/users",
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

    users = client.get("/api/v1/admin/users")
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

    audit = client.get("/api/v1/admin/audit", params={"subject": "INFY"})
    assert audit.status_code == 200
    assert len(audit.json()["result"]) == 1

    search = client.post(
        "/api/v1/admin/search",
        json={"query": "ops note", "scope": "audit"},
    )
    assert search.status_code == 200
    assert search.json()["result"]["count"] == 1

    export = client.get("/api/v1/admin/audit/export")
    assert export.status_code == 200
    assert export.json()["result"]["count"] == 1

    roles = client.get("/api/v1/admin/roles")
    assert roles.status_code == 200
    versions = client.get("/api/v1/admin/versions")
    assert versions.status_code == 200
    flags = client.get("/api/v1/admin/feature-flags")
    assert flags.status_code == 200


def test_admin_requires_bearer_when_enforced(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    created = client.post(
        "/api/v1/auth/rbac/users",
        json={
            "username": "adminops",
            "email": "adminops@example.com",
            "password": "StrongPass12!",
            "roles": ["administrator"],
            "user_id": "u-adminops",
            "created_at": FIXED,
            "password_salt": "aabbccddeeff0011",
        },
    )
    assert created.status_code == 200

    monkeypatch.setenv("DSP_REQUIRE_ADMIN_AUTH", "true")
    denied = client.get("/api/v1/admin/users")
    assert denied.status_code == 401

    login = client.post(
        "/api/v1/auth/rbac/login",
        json={
            "username": "adminops",
            "password": "StrongPass12!",
            "created_at": FIXED,
            "session_id": "s-adminops",
            "access_jti": "a-adminops",
            "refresh_jti": "r-adminops",
        },
    )
    assert login.status_code == 200
    token = login.json()["result"]["tokens"]["access_token"]
    allowed = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert allowed.status_code == 200
