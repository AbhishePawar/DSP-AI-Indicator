"""RC1 Milestone 9 — SaaS thin API tests (P0-05 — server identity)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from auth_test_helpers import bearer_headers, register_user
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.saas_platform import reset_saas_overlay_store_for_tests
from enterprise import EnterpriseService, reset_enterprise_service_for_tests


@pytest.fixture()
def platform() -> DSPPlatform:
    reset_enterprise_service_for_tests(EnterpriseService())
    reset_saas_overlay_store_for_tests()
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )


@pytest.fixture()
def client(platform: DSPPlatform) -> TestClient:
    return TestClient(create_app(platform=platform))


def test_schema_and_plans(client: TestClient) -> None:
    schema = client.get("/api/v1/saas/schema")
    assert schema.status_code == 200
    assert schema.json()["ok"] is True
    plans = client.get("/api/v1/saas/plans")
    assert plans.status_code == 200
    assert plans.json()["ok"] is True
    assert len(plans.json()["result"]["plans"]) == 4


def test_org_lifecycle(client: TestClient) -> None:
    assert client.get("/api/v1/saas/organizations").status_code == 401

    register_user(client, user_id="api-owner", username="apiowner")
    headers = bearer_headers(client, username="apiowner")
    created = client.post(
        "/api/v1/saas/organization",
        headers={**headers, "X-User-Id": "spoofed"},
        json={
            "name": "API Org",
            "slug": "api-org",
            "owner_user_id": "spoofed",
            "plan_id": "starter",
        },
    )
    body = created.json()
    assert created.status_code == 200, body
    assert body["ok"] is True, body
    org_id = body["result"]["organization"]["org_id"]
    assert body["result"]["organization"]["owner_user_id"] == "api-owner"

    listed = client.get("/api/v1/saas/organizations", headers=headers)
    assert listed.status_code == 200
    assert any(
        o["org_id"] == org_id for o in listed.json()["result"]["organizations"]
    )

    settings = client.put(
        f"/api/v1/saas/organization/{org_id}/settings",
        headers=headers,
        json={"timezone": "UTC", "currency": "USD"},
    )
    assert settings.status_code == 200

    sub = client.get(
        f"/api/v1/saas/organization/{org_id}/subscription",
        headers=headers,
    )
    assert sub.status_code == 200
    assert sub.json()["result"]["subscription"]["plan_id"] == "starter"


def test_subscription_license_usage(client: TestClient) -> None:
    register_user(client, user_id="bill-owner", username="billowner")
    headers = bearer_headers(client, username="billowner")
    created = client.post(
        "/api/v1/saas/organization",
        headers=headers,
        json={
            "name": "Bill Org",
            "slug": "bill-org",
            "owner_user_id": "bill-owner",
        },
    )
    org_id = created.json()["result"]["organization"]["org_id"]

    sub = client.post(
        "/api/v1/saas/subscription",
        headers=headers,
        json={
            "org_id": org_id,
            "plan_id": "enterprise",
            "actor_user_id": "spoofed",
        },
    )
    assert sub.status_code == 200
    assert sub.json()["result"]["payments_executed"] is False

    usage = client.post(
        "/api/v1/saas/usage",
        headers=headers,
        json={"org_id": org_id, "metric": "exports", "amount": 2},
    )
    assert usage.status_code == 200

    dash = client.get("/api/v1/saas/dashboard", headers=headers)
    assert dash.status_code == 200
    assert dash.json()["result"]["revenue"]["available"] is False


def test_checkout_unavailable(client: TestClient) -> None:
    register_user(client, user_id="pay-owner", username="payowner")
    headers = bearer_headers(client, username="payowner")
    created = client.post(
        "/api/v1/saas/organization",
        headers=headers,
        json={
            "name": "Pay Org",
            "slug": "pay-org",
            "owner_user_id": "pay-owner",
        },
    )
    org_id = created.json()["result"]["organization"]["org_id"]
    checkout = client.post(
        "/api/v1/saas/checkout",
        headers=headers,
        json={"org_id": org_id, "plan_id": "starter"},
    )
    assert checkout.status_code == 200
    body = checkout.json()
    assert body.get("ok") is True
    result = body.get("result") or {}
    # Checkout remains provider-unavailable (no fabricated payments).
    assert result.get("available") is False or result.get("payments_executed") is False or (
        "unavailable" in str(result).lower()
        or "unavailable" in str(body.get("message") or "").lower()
    )
