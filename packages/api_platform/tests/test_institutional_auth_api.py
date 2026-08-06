"""EPIC-A009 institutional auth API smoke tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform.api.app import create_app
from auth import AuthService, RoleRegistry, reset_auth_service_for_tests, reset_role_registry_for_tests
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
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
    reset_auth_service_for_tests(AuthService(ps, jwt_secret="test-secret"))
    app = create_app(enable_security=False)
    with TestClient(app) as c:
        yield c
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


def test_rbac_schema(client: TestClient) -> None:
    r = client.get("/api/v1/auth/rbac/schema")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "permissions" in body["schema"]


def test_user_crud_login_me_protect(client: TestClient) -> None:
    created = client.post(
        "/api/v1/auth/rbac/users",
        json={
            "username": "apiuser",
            "email": "api@example.com",
            "password": "StrongPass12!",
            "roles": ["research_analyst"],
            "user_id": "u-api",
            "created_at": FIXED,
            "password_salt": "aabbccddeeff0011",
        },
    )
    assert created.status_code == 200
    assert created.json()["result"]["username"] == "apiuser"

    login = client.post(
        "/api/v1/auth/rbac/login",
        json={
            "username": "apiuser",
            "password": "StrongPass12!",
            "created_at": FIXED,
            "session_id": "s-api",
            "access_jti": "a-api",
            "refresh_jti": "r-api",
        },
    )
    assert login.status_code == 200
    token = login.json()["result"]["tokens"]["access_token"]

    me = client.get(
        "/api/v1/auth/rbac/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.json()["result"]["user_id"] == "u-api"

    ok = client.post(
        "/api/v1/auth/rbac/protect?permission=read_research",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ok.status_code == 200

    denied = client.post(
        "/api/v1/auth/rbac/protect?permission=manage_users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert denied.status_code == 403

    roles = client.get("/api/v1/auth/rbac/roles")
    assert roles.status_code == 200
    assert any(r["role_id"] == "administrator" for r in roles.json()["result"])


def test_rbac_refresh_rotates_and_detects_reuse(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/rbac/users",
        json={
            "username": "refreshuser",
            "email": "refresh@example.com",
            "password": "StrongPass12!",
            "user_id": "u-refresh",
            "created_at": FIXED,
            "password_salt": "aabbccddeeff0011",
        },
    )
    login = client.post(
        "/api/v1/auth/rbac/login",
        json={
            "username": "refreshuser",
            "password": "StrongPass12!",
            "created_at": FIXED,
        },
    )
    assert login.status_code == 200
    old_refresh = login.json()["result"]["tokens"]["refresh_token"]

    first = client.post(
        "/api/v1/auth/rbac/refresh", json={"refresh_token": old_refresh}
    )
    assert first.status_code == 200
    new_refresh = first.json()["result"]["tokens"]["refresh_token"]
    assert new_refresh != old_refresh

    # Replaying the already-rotated-away refresh token is rejected...
    replay = client.post(
        "/api/v1/auth/rbac/refresh", json={"refresh_token": old_refresh}
    )
    assert replay.status_code == 401

    # ...and the entire session (family) is revoked, killing the rotated
    # token too even though it was never itself replayed.
    second = client.post(
        "/api/v1/auth/rbac/refresh", json={"refresh_token": new_refresh}
    )
    assert second.status_code == 401


def test_rbac_refresh_requires_token(client: TestClient) -> None:
    response = client.post("/api/v1/auth/rbac/refresh", json={})
    assert response.status_code == 401
