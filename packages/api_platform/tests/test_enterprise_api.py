"""EPS-002 enterprise API smoke tests (P0-05 — server identity only)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform.api.app import create_app
from auth_test_helpers import admin_headers, bearer_headers, register_user
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

    # P0-05 — unauthenticated list fails closed
    denied = client.get("/api/v1/enterprise/organizations")
    assert denied.status_code == 401

    register_user(client, user_id="u-acme", username="acmeowner")
    headers = bearer_headers(client, username="acmeowner")

    empty = client.get("/api/v1/enterprise/organizations", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["message"] == "No organizations available."

    created = client.post(
        "/api/v1/enterprise/organizations",
        headers=headers,
        json={
            "name": "Acme Research",
            "slug": "acme-research",
            "owner_user_id": "spoofed-owner",
            "seat_limit": 10,
        },
    )
    assert created.status_code == 200
    org_id = created.json()["result"]["org_id"]
    # Client-supplied owner_user_id must not win over JWT principal.
    assert created.json()["result"]["owner_user_id"] == "u-acme"

    portal = client.get(
        f"/api/v1/enterprise/organizations/{org_id}/portal",
        headers={**headers, "X-User-Id": "spoofed"},
    )
    assert portal.status_code == 200
    body = portal.json()["result"]
    assert body["billing"]["message"] == "Billing unavailable."
    assert body["license"]["message"] == "No license assigned."

    lic = client.post(
        f"/api/v1/enterprise/organizations/{org_id}/license",
        headers=headers,
        json={"actor_user_id": "spoofed", "tier": "enterprise", "seats": 25},
    )
    assert lic.status_code == 200
    assert lic.json()["result"]["tier"] == "enterprise"


def test_api_key_secret_not_leaked_on_list(client: TestClient) -> None:
    register_user(client, user_id="u-key", username="keyowner")
    headers = bearer_headers(client, username="keyowner")
    org = client.post(
        "/api/v1/enterprise/organizations",
        headers=headers,
        json={
            "name": "Key Org",
            "slug": "key-org",
            "owner_user_id": "u-key",
        },
    ).json()["result"]
    created = client.post(
        f"/api/v1/enterprise/organizations/{org['org_id']}/api-keys",
        headers=headers,
        json={
            "actor_user_id": "spoofed",
            "name": "prod",
            "scopes": ["org.view"],
        },
    )
    assert created.status_code == 200
    assert "secret" in created.json()["result"]

    listed = client.get(
        f"/api/v1/enterprise/organizations/{org['org_id']}/api-keys",
        headers={**headers, "X-User-Id": "other"},
    )
    assert listed.status_code == 200
    keys = listed.json()["result"]["keys"]
    assert keys
    assert "secret" not in keys[0]
    assert "secret_hash" not in keys[0]


def test_session_revoke_and_audit_immutable(client: TestClient) -> None:
    register_user(client, user_id="u-aud", username="audowner")
    headers = bearer_headers(client, username="audowner")
    org = client.post(
        "/api/v1/enterprise/organizations",
        headers=headers,
        json={
            "name": "Audit Org",
            "slug": "audit-org",
            "owner_user_id": "u-aud",
        },
    ).json()["result"]
    session = client.post(
        f"/api/v1/enterprise/organizations/{org['org_id']}/sessions",
        headers=headers,
        json={"user_id": "spoofed", "device_label": "browser"},
    ).json()["result"]

    revoked = client.post(
        f"/api/v1/enterprise/organizations/{org['org_id']}/sessions/"
        f"{session['session_id']}/revoke",
        headers=headers,
    )
    assert revoked.status_code == 200
    assert revoked.json()["result"]["status"] == "revoked"

    audit = client.get(
        f"/api/v1/enterprise/organizations/{org['org_id']}/audit",
        headers=headers,
    )
    assert audit.status_code == 200
    event_id = audit.json()["result"][0]["event_id"]
    denied = client.delete(
        f"/api/v1/enterprise/organizations/{org['org_id']}/audit/{event_id}",
        headers=headers,
    )
    assert denied.status_code == 403


def test_ops_and_collaboration_architecture(client: TestClient) -> None:
    # P0-05 — enterprise ops require admin JWT
    ops = client.get("/api/v1/enterprise/ops/dashboard")
    assert ops.status_code == 401

    headers = admin_headers(client)
    ops = client.get("/api/v1/enterprise/ops/dashboard", headers=headers)
    assert ops.status_code == 200
    assert ops.json()["result"]["billing_available"] is False

    collab = client.get("/api/v1/enterprise/collaboration/architecture")
    assert collab.status_code == 200
    assert collab.json()["result"]["realtime"] is False


def test_rbac_permission_gate_on_members(client: TestClient) -> None:
    register_user(client, user_id="u-owner", username="rbacowner")
    owner = bearer_headers(client, username="rbacowner")
    register_user(
        client,
        user_id="u-guest",
        username="rbacguest",
        roles=["read_only"],
    )
    guest = bearer_headers(client, username="rbacguest")

    org = client.post(
        "/api/v1/enterprise/organizations",
        headers=owner,
        json={
            "name": "RBAC Org",
            "slug": "rbac-org",
            "owner_user_id": "u-owner",
        },
    ).json()["result"]
    client.post(
        f"/api/v1/enterprise/organizations/{org['org_id']}/members",
        headers=owner,
        json={
            "actor_user_id": "spoofed",
            "user_id": "u-guest",
            "role_id": "guest",
        },
    )
    denied = client.get(
        f"/api/v1/enterprise/organizations/{org['org_id']}/members",
        headers=guest,
    )
    assert denied.status_code == 403

    # Spoofed X-User-Id must not elevate guest to owner.
    spoofed = client.get(
        f"/api/v1/enterprise/organizations/{org['org_id']}/members",
        headers={**guest, "X-User-Id": "u-owner"},
    )
    assert spoofed.status_code == 403

    allowed = client.get(
        f"/api/v1/enterprise/organizations/{org['org_id']}/members",
        headers=owner,
    )
    assert allowed.status_code == 200


def test_institutional_admin_wired(client: TestClient) -> None:
    """Prior A010 router registration gap closed by EPS-002."""
    headers = admin_headers(client, user_id="u-admin-wired", username="adminwired")
    schema = client.get("/api/v1/admin/schema", headers=headers)
    assert schema.status_code == 200
    assert schema.json()["ok"] is True


def test_client_header_never_authoritative(client: TestClient) -> None:
    """P0-05 acceptance — X-User-Id alone cannot authorize."""
    assert (
        client.get(
            "/api/v1/enterprise/organizations",
            headers={"X-User-Id": "attacker"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/enterprise/organizations",
            headers={"X-User-Id": "attacker"},
            json={
                "name": "Evil",
                "slug": "evil-org",
                "owner_user_id": "attacker",
            },
        ).status_code
        == 401
    )
