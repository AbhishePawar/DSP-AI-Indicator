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
    assert len(data["providers"]) == 3
