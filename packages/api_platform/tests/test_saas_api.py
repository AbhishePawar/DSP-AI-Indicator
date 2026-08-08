"""RC1 Milestone 9 — SaaS thin API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.saas_platform import reset_saas_overlay_store_for_tests
from enterprise import EnterpriseService, reset_enterprise_service_for_tests


@pytest.fixture()
def platform() -> DSPPlatform:
    # Force in-memory enterprise store so TestClient lifespan cannot attach DB.
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
    headers = {"X-User-Id": "api-owner"}
    created = client.post(
        "/api/v1/saas/organization",
        headers=headers,
        json={
            "name": "API Org",
            "slug": "api-org",
            "owner_user_id": "api-owner",
            "plan_id": "starter",
        },
    )
    body = created.json()
    assert created.status_code == 200, body
    assert body["ok"] is True, body
    org_id = body["result"]["organization"]["org_id"]

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

    sub = client.get(f"/api/v1/saas/organization/{org_id}/subscription")
    assert sub.status_code == 200
    assert sub.json()["result"]["subscription"]["plan_id"] == "starter"


def test_subscription_license_usage(client: TestClient) -> None:
    headers = {"X-User-Id": "bill-owner"}
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
            "actor_user_id": "bill-owner",
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

    dash = client.get("/api/v1/saas/dashboard")
    assert dash.status_code == 200
    assert dash.json()["result"]["revenue"]["available"] is False


def test_checkout_unavailable(client: TestClient) -> None:
    headers = {"X-User-Id": "pay-owner"}
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
        json={"org_id": org_id, "plan_id": "professional"},
    )
    assert checkout.status_code == 200
    result = checkout.json()["result"]
    assert result.get("ok") is False or result.get("available") is False
