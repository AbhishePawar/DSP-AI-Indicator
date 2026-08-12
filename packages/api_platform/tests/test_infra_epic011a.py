"""EPIC-011A — API infrastructure wiring and dependency health."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

from api_platform.api.app import create_app
from api_platform.api.infra_bootstrap import bootstrap_production_infrastructure
from dsp_platform import PlatformBuilder, PlatformConfiguration


def _client() -> TestClient:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    return TestClient(create_app(platform=platform))


def test_bootstrap_offline_memory_adapters() -> None:
    previous = os.environ.get("DSP_INFRA_OFFLINE")
    os.environ["DSP_INFRA_OFFLINE"] = "true"
    try:
        boot = bootstrap_production_infrastructure(force_offline=True)
        assert boot.infrastructure is not None
        assert boot.production is not None
        assert boot.infrastructure.database.ping() is True
    finally:
        if previous is None:
            os.environ.pop("DSP_INFRA_OFFLINE", None)
        else:
            os.environ["DSP_INFRA_OFFLINE"] = previous


def test_health_includes_database_and_redis_checks() -> None:
    client = _client()
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    names = {c.get("name") for c in data.get("checks", [])}
    assert "database" in names
    assert "redis" in names
    components = data.get("components") or {}
    assert "database" in components
    assert "redis" in components


def test_ready_snapshot_includes_dependencies() -> None:
    client = _client()
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert "dependencies" in data
    assert data["service_readiness"].get("infrastructure") is True
