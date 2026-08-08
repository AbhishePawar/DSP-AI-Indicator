"""P1.3 — Monitoring, health, logging, and lifecycle tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api_platform.api.app import create_app
from api_platform.api.monitoring import (
    PlatformLifecycleState,
    classify_error,
    mark_lifecycle,
    ops_logger,
    redact_sensitive,
)
from api_platform.api.ops import metrics_registry
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
    assert "lifecycle" in data
    assert "application_version" in data


def test_health_ready_includes_components() -> None:
    client = _client()
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert "platform_status" in data
    assert data["platform_status"] in {"ready", "degraded"}
    assert "components" in data
    assert "application" in data["components"]
    assert "api" in data["components"]
    assert "research_service" in data["components"]
    assert "overall" in data["components"]
    assert "resources" in data
    assert "llm" in data
    assert data["llm"]["blocking"] is False


def test_health_overall_components() -> None:
    client = _client()
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "components" in data
    assert data["components"]["overall"]["status"] in {"pass", "fail"}
    assert data.get("platform_status") in {"ready", "degraded", "unhealthy", "startup"}


def test_metrics_prometheus_ops_counters() -> None:
    client = _client()
    client.get("/health")
    client.get("/version")
    response = client.get("/metrics")
    assert response.status_code == 200
    text = response.text
    assert "dsp_http_requests_total" in text
    assert "dsp_api_latency_ms_last" in text
    assert "dsp_build_info" in text
    assert "dsp_system_restarts_total" in text


def test_redaction_never_logs_secrets() -> None:
    cleaned = redact_sensitive(
        {
            "password": "hunter2",
            "authorization": "Bearer abc.def.ghi",
            "nested": {"api_key": "secret", "ticker": "AAPL"},
        }
    )
    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["authorization"] == "[REDACTED]"
    assert cleaned["nested"]["api_key"] == "[REDACTED]"
    assert cleaned["nested"]["ticker"] == "AAPL"
    assert "Bearer abc" not in str(cleaned)


def test_classify_error_severity() -> None:
    assert classify_error(status_code=500).value == "critical"
    assert classify_error(status_code=401).value == "warning"
    assert classify_error(status_code=429).value == "warning"


def test_ops_logger_captures_without_secrets() -> None:
    ops_logger.log(
        "INFO",
        "authentication",
        correlation_id="corr-test",
        fields={"password": "nope", "path": "/auth/login"},
    )
    recent = ops_logger.recent(20)
    last = next(r for r in reversed(recent) if r.get("correlation_id") == "corr-test")
    assert last["fields"]["password"] == "[REDACTED]"
    assert last["message"] == "authentication"


def test_graceful_shutdown_lifecycle() -> None:
    mark_lifecycle(PlatformLifecycleState.READY)
    client = _client()
    assert client.get("/health/live").status_code == 200
    # Lifespan shutdown runs when context exits.
    with TestClient(create_app()) as c:
        assert c.get("/health/live").json()["status"] == "alive"
    assert True  # shutdown hooks ran without raising


def test_versioned_health_aliases() -> None:
    client = _client()
    assert client.get("/api/v1/health/live").status_code == 200
    assert client.get("/api/v1/health/ready").status_code == 200
    assert client.get("/api/v1/metrics").status_code == 200


def test_metrics_note_path_analysis() -> None:
    metrics_registry.note_path("/api/v1/analyse", status_code=200, elapsed_ms=12.5)
    text = metrics_registry.render_prometheus()
    assert "dsp_analysis_requests_total" in text
    assert "dsp_analysis_duration_ms_last" in text
