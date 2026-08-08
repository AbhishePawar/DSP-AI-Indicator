"""RC1 Milestone 11 — Control Center thin API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.control_center import reset_configuration_registry_for_tests


@pytest.fixture()
def platform() -> DSPPlatform:
    reset_configuration_registry_for_tests()
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )


@pytest.fixture()
def client(platform: DSPPlatform) -> TestClient:
    return TestClient(create_app(platform=platform))


def test_schema_and_registry(client: TestClient) -> None:
    schema = client.get("/api/v1/admin/control-center/schema")
    assert schema.status_code == 200
    assert schema.json()["ok"] is True
    assert "branding" in schema.json()["schema"]["modules"]

    registry = client.get("/api/v1/admin/configuration/registry")
    assert registry.status_code == 200
    body = registry.json()
    assert body["ok"] is True
    assert "branding" in body["result"]["modules"]

    # A010 read path still intact
    legacy = client.get("/api/v1/admin/configuration")
    assert legacy.status_code == 200
    assert legacy.json()["ok"] is True


def test_configuration_update_rollback(client: TestClient) -> None:
    headers = {"X-User-Id": "cc-admin"}
    updated = client.post(
        "/api/v1/admin/configuration",
        headers=headers,
        json={
            "module_id": "branding",
            "configuration": {"theme": "light"},
            "reason": "api test",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["ok"] is True
    version = updated.json()["result"]["change"]["version"]

    history = client.get("/api/v1/admin/configuration/history")
    assert history.status_code == 200
    assert any(
        h["version"] == version for h in history.json()["result"]["history"]
    )

    rolled = client.post(
        "/api/v1/admin/rollback",
        headers=headers,
        json={"version": version, "reason": "api rollback"},
    )
    assert rolled.status_code == 200
    assert rolled.json()["ok"] is True
    assert rolled.json()["result"]["rolled_back_to"] == version


def test_feature_flags_business_rules_security(client: TestClient) -> None:
    headers = {"X-User-Id": "cc-admin"}
    flags = client.post(
        "/api/v1/admin/feature-flags/overrides",
        headers=headers,
        json={"flag": "exports", "enabled": False, "reason": "api flag"},
    )
    assert flags.status_code == 200
    assert flags.json()["result"]["configuration"]["exports"] is False

    rule = client.post(
        "/api/v1/admin/business-rules",
        headers=headers,
        json={
            "name": "portfolio-health",
            "category": "portfolio",
            "condition": {"metric": "health", "op": "lt", "value": 50},
            "action": {"type": "alert"},
        },
    )
    assert rule.status_code == 200
    rule_id = rule.json()["result"]["rule"]["rule_id"]

    listed = client.get("/api/v1/admin/business-rules")
    assert listed.status_code == 200
    assert any(r["rule_id"] == rule_id for r in listed.json()["result"]["rules"])

    sec = client.post(
        "/api/v1/admin/security/config",
        headers=headers,
        json={"configuration": {"mfa_required": True}},
    )
    assert sec.status_code == 200
    assert sec.json()["result"]["configuration"]["mfa_required"] is True

    deleted = client.delete(
        f"/api/v1/admin/business-rules/{rule_id}", headers=headers
    )
    assert deleted.status_code == 200
    assert deleted.json()["result"]["deleted"] is True


def test_module_posts_and_monitoring(client: TestClient) -> None:
    headers = {"X-User-Id": "cc-admin"}
    for path, payload in (
        ("/api/v1/admin/branding", {"configuration": {"theme": "system"}}),
        ("/api/v1/admin/valuation/config", {"configuration": {"wacc_default": 0.1}}),
        ("/api/v1/admin/ai/config", {"configuration": {"temperature": 0.2}}),
        ("/api/v1/admin/market/config", {"configuration": {"default_currency": "INR"}}),
    ):
        res = client.post(path, headers=headers, json=payload)
        assert res.status_code == 200, path
        assert res.json()["ok"] is True

    mon = client.get("/api/v1/admin/monitoring")
    assert mon.status_code == 200
    assert mon.json()["ok"] is True

    audit = client.get("/api/v1/admin/audit/config")
    assert audit.status_code == 200
    assert isinstance(audit.json()["result"]["audit"], list)

    dash = client.get("/api/v1/admin/control-center/dashboard")
    assert dash.status_code == 200
    assert dash.json()["ok"] is True
