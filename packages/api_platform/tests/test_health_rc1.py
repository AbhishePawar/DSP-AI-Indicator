"""RC1 health and metrics endpoint tests (EPIC-013)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api_platform.api.app import create_app
from dsp_platform import PlatformBuilder, PlatformConfiguration


def _client() -> TestClient:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    return TestClient(create_app(platform=platform))


def test_health_live() -> None:
    client = _client()
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "application_version" in data


def test_health_ready() -> None:
    client = _client()
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert "llm" in data
    assert data["llm"]["blocking"] is False
    assert "build" in data


def test_metrics_prometheus() -> None:
    client = _client()
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "dsp_http_requests_total" in response.text
    assert "dsp_build_info" in response.text


def test_versioned_health_aliases() -> None:
    client = _client()
    assert client.get("/api/v1/health/live").status_code == 200
    assert client.get("/api/v1/health/ready").status_code == 200
    assert client.get("/api/v1/metrics").status_code == 200
