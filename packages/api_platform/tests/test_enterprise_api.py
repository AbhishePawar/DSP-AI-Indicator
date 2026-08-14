"""EPS-002 enterprise API smoke tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform.api.app import create_app
from enterprise import EnterpriseService, reset_enterprise_service_for_tests


@pytest.fixture()
def client() -> TestClient:
    svc = EnterpriseService()
    reset_enterprise_service_for_tests(svc)
    app = create_app(enable_security=False)
    with TestClient(app) as c:
        yield c
    reset_enterprise_service_for_tests(None)


def test_enterprise_schema_and_org_portal(client: TestClient) -> None:
    schema = client.get("/api/v1/enterprise/schema")
    assert schema.status_code == 200
    assert schema.json()["ok"] is True
    assert "organizations" in schema.json()["schema"]["capabilities"]

    empty = client.get("/api/v1/enterprise/organizations")
    assert empty.status_code == 200
    assert empty.json()["message"] == "No organizations available."

    created = client.post(
        "/api/v1/enterprise/organizations",
        json={
            "name": "Acme Research",
            "slug": "acme-research",
            "owner_user_id": "u-acme",
            "seat_limit": 10,
        },
    )
    assert created.status_code == 200
    org_id = created.json()["result"]["org_id"]

    portal = client.get(
        f"/api/v1/enterprise/organizations/{org_id}/portal",
        headers={"X-User-Id": "u-acme"},
    )
    assert portal.status_code == 200
    body = portal.json()["result"]
    assert body["billing"]["message"] == "Billing unavailable."
    assert body["license"]["message"] == "No license assigned."

    lic = client.post(
        f"/api/v1/enterprise/organizations/{org_id}/license",
        json={"actor_user_id": "u-acme", "tier": "enterprise", "seats": 25},
    )
    assert lic.status_code == 200
    assert lic.json()["result"]["tier"] == "enterprise"


def test_api_key_secret_not_leaked_on_list(client: TestClient) -> None:
    org = client.post(
        "/api/v1/enterprise/organizations",
        json={
            "name": "Key Org",
            "slug": "key-org",
            "owner_user_id": "u-key",
        },
    ).json()["result"]
    created = client.post(
        f"/api/v1/enterprise/organizations/{org['org_id']}/api-keys",
        json={
            "actor_user_id": "u-key",
            "name": "prod",
            "scopes": ["org.view"],
        },
    )
    assert created.status_code == 200
    assert "secret" in created.json()["result"]

    listed = client.get(
        f"/api/v1/enterprise/organizations/{org['org_id']}/api-keys",
        headers={"X-User-Id": "u-key"},
    )
    assert listed.status_code == 200
    keys = listed.json()["result"]["keys"]
    assert keys
    assert "secret" not in keys[0]
    assert "secret_hash" not in keys[0]


def test_session_revoke_and_audit_immutable(client: TestClient) -> None:
    org = client.post(
        "/api/v1/enterprise/organizations",
        json={
            "name": "Audit Org",
            "slug": "audit-org",
            "owner_user_id": "u-aud",
        },
    ).json()["result"]
    session = client.post(
        f"/api/v1/enterprise/organizations/{org['org_id']}/sessions",
        json={"user_id": "u-aud", "device_label": "browser"},
    ).json()["result"]

    revoked = client.post(
        f"/api/v1/enterprise/organizations/{org['org_id']}/sessions/"
        f"{session['session_id']}/revoke",
        headers={"X-User-Id": "u-aud"},
    )
    assert revoked.status_code == 200
    assert revoked.json()["result"]["status"] == "revoked"

    audit = client.get(
        f"/api/v1/enterprise/organizations/{org['org_id']}/audit",
        headers={"X-User-Id": "u-aud"},
    )
    assert audit.status_code == 200
    event_id = audit.json()["result"][0]["event_id"]
    denied = client.delete(
        f"/api/v1/enterprise/organizations/{org['org_id']}/audit/{event_id}"
    )
    assert denied.status_code == 403


def test_ops_and_collaboration_architecture(client: TestClient) -> None:
    ops = client.get("/api/v1/enterprise/ops/dashboard")
    assert ops.status_code == 200
    assert ops.json()["result"]["billing_available"] is False

    collab = client.get("/api/v1/enterprise/collaboration/architecture")
    assert collab.status_code == 200
    assert collab.json()["result"]["realtime"] is False


def test_rbac_permission_gate_on_members(client: TestClient) -> None:
    org = client.post(
        "/api/v1/enterprise/organizations",
        json={
            "name": "RBAC Org",
            "slug": "rbac-org",
            "owner_user_id": "u-owner",
        },
    ).json()["result"]
    client.post(
        f"/api/v1/enterprise/organizations/{org['org_id']}/members",
        json={
            "actor_user_id": "u-owner",
            "user_id": "u-guest",
            "role_id": "guest",
        },
    )
    denied = client.get(
        f"/api/v1/enterprise/organizations/{org['org_id']}/members",
        headers={"X-User-Id": "u-guest"},
    )
    assert denied.status_code == 403

    allowed = client.get(
        f"/api/v1/enterprise/organizations/{org['org_id']}/members",
        headers={"X-User-Id": "u-owner"},
    )
    assert allowed.status_code == 200


def test_institutional_admin_wired(client: TestClient) -> None:
    """Prior A010 router registration gap closed by EPS-002."""
    schema = client.get("/api/v1/admin/schema")
    assert schema.status_code == 200
    assert schema.json()["ok"] is True
