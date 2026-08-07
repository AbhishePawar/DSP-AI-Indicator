"""RC1 Milestone 9 — SaaS platform unit tests."""

from __future__ import annotations

import pytest

from dsp_platform.saas_platform import (
    PLAN_IDS,
    compare_plans,
    reset_saas_overlay_store_for_tests,
    run_saas_platform,
    saas_platform_schema,
)
from enterprise import EnterpriseService, reset_enterprise_service_for_tests


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_enterprise_service_for_tests(EnterpriseService())
    reset_saas_overlay_store_for_tests()


def test_schema() -> None:
    schema = saas_platform_schema()
    assert schema["schema_version"] == "1.0.0"
    assert "starter" in schema["plans"]
    assert "reuse_enterprise_organizations" in schema["rules"]


def test_plan_comparison() -> None:
    matrix = compare_plans()
    assert len(matrix["plans"]) == 4
    assert set(PLAN_IDS) == {p["plan_id"] for p in matrix["plans"]}


def test_create_org_and_subscription() -> None:
    created = run_saas_platform(
        "create_organization",
        payload={
            "name": "Acme Research",
            "slug": "acme-research",
            "owner_user_id": "user-owner",
            "plan_id": "professional",
        },
    )
    assert created["ok"] is True
    org = created["result"]["organization"]
    org_id = org["org_id"]
    assert org["preferences"]["timezone"] == "UTC"

    sub = run_saas_platform(
        "get_subscription", payload={"org_id": org_id}
    )
    assert sub["ok"] is True
    assert sub["result"]["subscription"]["plan_id"] == "professional"

    lic = run_saas_platform(
        "get_license",
        payload={"org_id": org_id, "actor_user_id": "user-owner"},
    )
    assert lic["ok"] is True
    assert lic["result"]["license"]["tier"] == "professional"


def test_archive_and_settings() -> None:
    created = run_saas_platform(
        "create_organization",
        payload={
            "name": "Beta Desk",
            "slug": "beta-desk",
            "owner_user_id": "owner-2",
        },
    )
    org_id = created["result"]["organization"]["org_id"]
    settings = run_saas_platform(
        "update_settings",
        payload={
            "org_id": org_id,
            "actor_user_id": "owner-2",
            "timezone": "Asia/Kolkata",
            "currency": "INR",
            "primary_color": "#0f766e",
            "logo_url": "https://example.com/logo.png",
        },
    )
    assert settings["ok"] is True
    prefs = settings["result"]["organization"]["preferences"]
    assert prefs["timezone"] == "Asia/Kolkata"
    assert prefs["currency"] == "INR"

    archived = run_saas_platform(
        "archive_organization",
        payload={"org_id": org_id, "actor_user_id": "owner-2"},
    )
    assert archived["ok"] is True
    assert archived["result"]["organization"]["status"] == "archived"


def test_usage_and_api_key() -> None:
    created = run_saas_platform(
        "create_organization",
        payload={
            "name": "Gamma",
            "slug": "gamma-org",
            "owner_user_id": "owner-3",
            "plan_id": "starter",
        },
    )
    org_id = created["result"]["organization"]["org_id"]
    usage = run_saas_platform(
        "record_usage",
        payload={
            "org_id": org_id,
            "metric": "research",
            "amount": 3,
            "actor_user_id": "owner-3",
        },
    )
    assert usage["ok"] is True

    snap = run_saas_platform(
        "usage",
        payload={"org_id": org_id, "actor_user_id": "owner-3"},
    )
    assert snap["ok"] is True
    assert snap["result"]["research_count"] == 3

    key = run_saas_platform(
        "create_api_key",
        payload={
            "org_id": org_id,
            "actor_user_id": "owner-3",
            "name": "ci",
            "scopes": ["org.view"],
        },
    )
    assert key["ok"] is True
    assert key["result"]["api_key"]["secret_shown_once"] is True


def test_license_key_activation() -> None:
    created = run_saas_platform(
        "create_organization",
        payload={
            "name": "Delta",
            "slug": "delta-org",
            "owner_user_id": "owner-4",
        },
    )
    org_id = created["result"]["organization"]["org_id"]
    issued = run_saas_platform(
        "issue_license_key",
        payload={"plan_id": "enterprise", "seats": 25},
    )
    assert issued["ok"] is True
    license_key = issued["result"]["license_key"]["license_key"]

    activated = run_saas_platform(
        "activate_license",
        payload={
            "org_id": org_id,
            "license_key": license_key,
            "actor_user_id": "owner-4",
        },
    )
    assert activated["ok"] is True
    assert activated["result"]["organization_activated"] is True


def test_checkout_never_fakes_payment() -> None:
    created = run_saas_platform(
        "create_organization",
        payload={
            "name": "Epsilon",
            "slug": "epsilon-org",
            "owner_user_id": "owner-5",
        },
    )
    org_id = created["result"]["organization"]["org_id"]
    checkout = run_saas_platform(
        "checkout",
        payload={"org_id": org_id, "plan_id": "professional"},
    )
    assert checkout["ok"] is True
    result = checkout["result"]
    assert result.get("ok") is False or result.get("available") is False
    assert "unavailable" in str(result.get("message") or "").lower() or result.get(
        "checkout_enabled"
    ) is False


def test_admin_dashboard_honest_revenue() -> None:
    dash = run_saas_platform("dashboard")
    assert dash["ok"] is True
    revenue = dash["result"]["revenue"]
    assert revenue["available"] is False
    assert revenue["mrr"] is None
    assert "Data unavailable" in revenue["message"]
