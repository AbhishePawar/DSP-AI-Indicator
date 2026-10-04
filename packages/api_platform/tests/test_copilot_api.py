"""Copilot API tests — EPIC-012."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api_platform.api.app import create_app
from dsp_platform import PlatformBuilder, PlatformConfiguration


def _sample_body() -> dict:
    return {
        "question_id": "why_buy",
        "request": {
            "ticker": "AAPL",
            "company": "Apple",
            "exchange": "NASDAQ",
        },
        "response": {
            "ok": True,
            "payload": {
                "ok": True,
                "recommendation_summary": {
                    "decision": "Buy",
                    "confidence": 0.8,
                    "margin_of_safety": 0.2,
                },
                "committee_summary": {"decision": "Approve", "confidence": 0.7},
                "stage_summaries": [],
            },
        },
    }


def test_copilot_complete_deterministic_fallback() -> None:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(create_app(platform=platform))
    response = client.post("/api/v1/copilot/complete", json=_sample_body())
    assert response.status_code == 200
    data = response.json()
    assert data["provider_id"] == "deterministic"
    assert "Buy" in data["content"]


def test_copilot_stream_returns_sse() -> None:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(create_app(platform=platform))
    response = client.post("/api/v1/copilot/stream", json=_sample_body())
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert "data:" in response.text


def test_copilot_providers_discovery() -> None:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(create_app(platform=platform))
    response = client.get("/api/v1/copilot/providers")
    assert response.status_code == 200
    data = response.json()
    assert data["active_provider"] == "deterministic"
    assert len(data["providers"]) == 4


def test_copilot_complete_mode_buffett_allowed() -> None:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(create_app(platform=platform))
    body = _sample_body()
    body["mode"] = "buffett"
    response = client.post("/api/v1/copilot/complete", json=body)
    assert response.status_code == 200
    data = response.json()
    assert data["provider_id"] == "deterministic"
    assert "Buy" in data["content"]


def test_copilot_complete_mode_simple_forbidden() -> None:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(create_app(platform=platform))
    body = _sample_body()
    body["mode"] = "simple"
    response = client.post("/api/v1/copilot/complete", json=body)
    assert response.status_code == 403
    data = response.json()
    assert data["ok"] is False
    assert data["error"] == "COPILOT_NOT_AVAILABLE_IN_SIMPLE_MODE"
    assert "Buffett AI Indicator mode" in data["message"]


def test_copilot_stream_mode_simple_forbidden() -> None:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(create_app(platform=platform))
    body = _sample_body()
    body["mode"] = "simple"
    response = client.post("/api/v1/copilot/stream", json=body)
    assert response.status_code == 403
    data = response.json()
    assert data["ok"] is False
    assert data["error"] == "COPILOT_NOT_AVAILABLE_IN_SIMPLE_MODE"


def test_copilot_complete_invalid_mode_rejected() -> None:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(create_app(platform=platform))
    body = _sample_body()
    body["mode"] = "invalid_mode"
    response = client.post("/api/v1/copilot/complete", json=body)
    assert response.status_code == 422


def test_copilot_complete_omitted_mode_defaults_to_buffett() -> None:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(create_app(platform=platform))
    body = _sample_body()
    assert "mode" not in body
    response = client.post("/api/v1/copilot/complete", json=body)
    assert response.status_code == 200
    assert response.json()["provider_id"] == "deterministic"


def test_copilot_complete_with_authoritative_response() -> None:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(create_app(platform=platform))
    authoritative_body = {
        "mode": "buffett",
        "question_id": "freeform",
        "freeform": "What is the recommendation?",
        "request": {"ticker": "AAPL"},
        "response": {
            "ok": True,
            "capability": "compose_intelligence",
            "payload": {
                "ok": True,
                "ticker": "AAPL",
                "company": "Apple Inc",
                "recommendation_summary": {
                    "decision": "Strong Buy",
                    "confidence": 0.92,
                    "margin_of_safety": 0.35,
                },
                "committee_summary": {"decision": "Approve", "confidence": 0.88},
                "stage_summaries": [
                    {"stage": "business_quality_aggregator", "has_result": True, "label": "High Quality"}
                ],
            },
        },
    }
    response = client.post("/api/v1/copilot/complete", json=authoritative_body)
    assert response.status_code == 200
    data = response.json()
    assert "Strong Buy" in data["content"] or "Apple Inc" in data["content"]
