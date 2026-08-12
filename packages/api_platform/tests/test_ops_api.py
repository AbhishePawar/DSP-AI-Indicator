"""RC1 Milestone 10 — /ops/* thin API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration


@pytest.fixture()
def platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )


@pytest.fixture()
def client(platform: DSPPlatform) -> TestClient:
    return TestClient(create_app(platform=platform))


def test_ops_schema(client: TestClient) -> None:
    res = client.get("/api/v1/ops/schema")
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert "/ops/health" in res.json()["schema"]["routes"]


def test_ops_health_version_dependencies(client: TestClient) -> None:
    health = client.get("/api/v1/ops/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True
    version = client.get("/api/v1/ops/version")
    assert version.status_code == 200
    assert "application_version" in version.json()["result"]
    deps = client.get("/api/v1/ops/dependencies")
    assert deps.status_code == 200
    assert deps.json()["result"]["components"]


def test_ops_metrics_summary_and_prometheus(client: TestClient) -> None:
    summary = client.get("/api/v1/ops/metrics")
    assert summary.status_code == 200
    assert summary.json()["result"]["scrape_path"] == "/metrics"
    prom = client.get("/api/v1/ops/metrics", params={"format": "prometheus"})
    assert prom.status_code == 200
    assert "text/plain" in prom.headers.get("content-type", "")


def test_ops_backup_and_legacy_health(client: TestClient) -> None:
    backup = client.get("/api/v1/ops/backup")
    assert backup.status_code == 200
    assert backup.json()["result"]["available"] is False
    # Existing health routes remain
    assert client.get("/api/v1/health/live").status_code == 200
    startup = client.get("/api/v1/health/startup")
    assert startup.status_code in {200, 503}
    deps = client.get("/api/v1/health/dependencies")
    assert deps.status_code == 200


def test_ops_dashboard(client: TestClient) -> None:
    dash = client.get("/api/v1/ops/dashboard")
    assert dash.status_code == 200
    body = dash.json()
    assert body["ok"] is True
    assert "observability" in body["result"]
    assert "security_hardening" in body["result"]
