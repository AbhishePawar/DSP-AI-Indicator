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


def test_copilot_query_success_contract() -> None:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(create_app(platform=platform))
    response = client.post(
        "/api/v1/copilot/query",
        json={
            "query": "What is the economic moat of this company?",
            "symbol": "AAPL",
            "analysis_id": "test-analysis-123",
            "section_context": "Moat Assessment",
            "prompt": "Tell me more about the Moat Assessment.",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert data["provider_id"] == "deterministic"
    assert data["symbol"] == "AAPL"
    assert data["analysis_id"] == "test-analysis-123"
    assert data["section_context"] == "Moat Assessment"
    assert data["intent"] == "research_query"
    assert isinstance(data["citations"], list)
    assert isinstance(data["limitations"], list)


def test_copilot_query_missing_service_error() -> None:
    # When copilot_service is not configured, expect validation error or 422
    from api_platform.api.dependencies import ApiState
    app = create_app()
    app.state.api_state.copilot_service = None
    client = TestClient(app)
    response = client.post(
        "/api/v1/copilot/query",
        json={
            "query": "What is the moat?",
            "symbol": "AAPL",
        },
    )
    assert response.status_code in (400, 422, 503)
