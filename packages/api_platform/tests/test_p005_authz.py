"""P0-05 acceptance — server identity only; admin/ops/saas gated."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from auth import get_auth_service, reset_auth_service_for_tests
from auth_test_helpers import admin_headers, bearer_headers, register_user
from enterprise import EnterpriseService, reset_enterprise_service_for_tests


@pytest.fixture()
def client() -> TestClient:
    reset_enterprise_service_for_tests(EnterpriseService())
    reset_auth_service_for_tests(None)
    app = create_app(enable_security=False)
    with TestClient(app) as c:
        yield c
    reset_enterprise_service_for_tests(None)
    reset_auth_service_for_tests(None)


def test_x_user_id_never_authoritative_for_saas_or_enterprise(client: TestClient) -> None:
    spoof = {"X-User-Id": "attacker"}
    assert client.get("/api/v1/saas/organizations", headers=spoof).status_code == 401
    assert client.get("/api/v1/enterprise/organizations", headers=spoof).status_code == 401
    assert client.get("/api/v1/ops/secrets", headers=spoof).status_code == 401
    assert client.get("/api/v1/admin/schema", headers=spoof).status_code == 401


def test_authenticated_actor_ignores_spoofed_header(client: TestClient) -> None:
    register_user(client, user_id="u-real", username="realuser")
    headers = bearer_headers(client, username="realuser")
    created = client.post(
        "/api/v1/enterprise/organizations",
        headers={**headers, "X-User-Id": "attacker"},
        json={
            "name": "Real Org",
            "slug": "real-org-p005",
            "owner_user_id": "attacker",
        },
    )
    assert created.status_code == 200
    assert created.json()["result"]["owner_user_id"] == "u-real"


def test_ops_and_admin_require_admin_permission(client: TestClient) -> None:
    register_user(
        client,
        user_id="u-ro",
        username="readonlyp005",
        roles=["read_only"],
    )
    ro = bearer_headers(client, username="readonlyp005")
    assert client.get("/api/v1/ops/dashboard", headers=ro).status_code == 403
    assert client.get("/api/v1/admin/schema", headers=ro).status_code == 403

    admin = admin_headers(client, user_id="u-p005a", username="p005adminx")
    assert client.get("/api/v1/ops/dashboard", headers=admin).status_code == 200
    assert client.get("/api/v1/admin/schema", headers=admin).status_code == 200


def test_auth_jwt_secret_fail_closed_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_auth_service_for_tests(None)
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.delenv("DSP_AUTH_JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="DSP_AUTH_JWT_SECRET"):
        get_auth_service()
    reset_auth_service_for_tests(None)
