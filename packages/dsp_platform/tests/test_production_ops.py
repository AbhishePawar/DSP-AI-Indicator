"""RC1 Milestone 10 — Production Operations unit tests."""

from __future__ import annotations

from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.production_ops import (
    production_ops_schema,
    run_production_ops,
)
from production_platform.production.backup import NullBackupAdapter


def _platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )


def test_schema() -> None:
    schema = production_ops_schema()
    assert schema["schema_version"] == "1.0.0"
    assert "/ops/health" in schema["routes"]
    assert "no_duplicated_monitoring" in schema["rules"]


def test_live_and_version() -> None:
    platform = _platform()
    live = run_production_ops("live", platform=platform)
    assert live["ok"] is True
    assert live["result"]["status"] == "alive"
    version = run_production_ops("version", platform=platform)
    assert version["ok"] is True
    assert "application_version" in version["result"]


def test_health_and_ready() -> None:
    platform = _platform()
    health = run_production_ops("health", platform=platform)
    assert health["ok"] is True
    assert "live" in health["result"]
    assert "ready" in health["result"]
    ready = run_production_ops("ready", platform=platform)
    assert ready["ok"] is True
    assert "ready" in ready["result"]


def test_dependencies_and_observability() -> None:
    platform = _platform()
    deps = run_production_ops("dependencies", platform=platform)
    assert deps["ok"] is True
    names = {c["name"] for c in deps["result"]["components"]}
    assert "platform" in names
    assert "database" in names
    obs = run_production_ops("observability", platform=platform)
    assert obs["ok"] is True
    assert obs["result"]["structured_logging"]["format"] == "json"
    assert obs["result"]["prometheus"]["path"] == "/metrics"


def test_backup_never_fakes() -> None:
    platform = _platform()
    status = run_production_ops("backup", platform=platform)
    assert status["ok"] is True
    assert status["result"]["available"] is False
    create = run_production_ops(
        "backup", platform=platform, payload={"backup_action": "create"}
    )
    assert create["ok"] is True
    assert create["result"].get("ok") is False
    adapter = NullBackupAdapter()
    assert adapter.is_available() is False


def test_dashboard_and_platform_methods() -> None:
    platform = _platform()
    schema = platform.production_ops_schema()
    assert "routes" in schema
    dash = platform.run_production_ops("dashboard")
    assert dash["ok"] is True
    assert dash["result"]["backup"]["available"] is False
    assert "ci_cd" in dash["result"]
