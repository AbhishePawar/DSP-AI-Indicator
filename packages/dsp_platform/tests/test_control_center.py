"""RC1 Milestone 11 — Super Admin Control Center unit tests."""

from __future__ import annotations

from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.control_center import (
    control_center_schema,
    get_configuration_registry,
    reset_configuration_registry_for_tests,
    run_control_center,
)


def _platform() -> DSPPlatform:
    reset_configuration_registry_for_tests()
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )


def test_schema() -> None:
    schema = control_center_schema()
    assert schema["schema_version"] == "1.0.0"
    assert "branding" in schema["modules"]
    assert "valuation" in schema["modules"]
    assert "never_execute_engines" in schema["rules"]
    assert "/admin/rollback" in schema["routes"]


def test_update_and_rollback() -> None:
    platform = _platform()
    updated = run_control_center(
        "update_configuration",
        platform=platform,
        payload={
            "module_id": "branding",
            "configuration": {"theme": "dark", "company_name": "DSP"},
            "author": "tester",
            "reason": "unit test branding",
        },
    )
    assert updated["ok"] is True
    version = updated["result"]["change"]["version"]
    assert updated["result"]["configuration"]["theme"] == "dark"

    reg = get_configuration_registry()
    assert reg.get_module("branding")["theme"] == "dark"

    rolled = run_control_center(
        "rollback",
        platform=platform,
        payload={"version": version, "author": "tester", "reason": "undo"},
    )
    assert rolled["ok"] is True
    assert rolled["result"]["rolled_back_to"] == version
    # Prior default theme restored
    assert rolled["result"]["configuration"].get("theme") == "system"


def test_feature_flags_and_business_rules() -> None:
    platform = _platform()
    flags = run_control_center(
        "feature_flags",
        platform=platform,
        payload={
            "flag": "copilot",
            "enabled": False,
            "author": "tester",
            "reason": "disable copilot",
        },
    )
    assert flags["ok"] is True
    assert flags["result"]["configuration"]["copilot"] is False

    rule = run_control_center(
        "business_rules_upsert",
        platform=platform,
        payload={
            "name": "mos-alert",
            "category": "alerts",
            "condition": {"metric": "mos", "op": "lt", "value": 0.2},
            "action": {"type": "notify"},
            "author": "tester",
        },
    )
    assert rule["ok"] is True
    rule_id = rule["result"]["rule"]["rule_id"]
    listed = run_control_center("business_rules_list", platform=platform)
    assert any(r["rule_id"] == rule_id for r in listed["result"]["rules"])

    deleted = run_control_center(
        "business_rules_delete",
        platform=platform,
        payload={"rule_id": rule_id, "author": "tester"},
    )
    assert deleted["ok"] is True
    assert deleted["result"]["deleted"] is True


def test_security_and_valuation_overlays_no_engines() -> None:
    platform = _platform()
    sec = run_control_center(
        "security",
        platform=platform,
        payload={
            "configuration": {"session_timeout_minutes": 45},
            "author": "tester",
        },
    )
    assert sec["ok"] is True
    assert sec["result"]["configuration"]["session_timeout_minutes"] == 45

    val = run_control_center(
        "valuation",
        platform=platform,
        payload={
            "configuration": {"margin_of_safety_default": 0.35},
            "author": "tester",
            "reason": "overlay only",
        },
    )
    assert val["ok"] is True
    assert val["provenance"]["engines_executed"] is False


def test_platform_methods() -> None:
    platform = _platform()
    schema = platform.control_center_schema()
    assert "modules" in schema
    dash = platform.run_control_center("dashboard")
    assert dash["ok"] is True
    assert "modules" in dash["result"]
    hist = platform.run_control_center("history", payload={"limit": 5})
    assert hist["ok"] is True
    assert isinstance(hist["result"]["history"], list)
