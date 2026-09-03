"""Copilot API tests — EPIC-012 + production AI activation boundary."""

from __future__ import annotations

from auth_test_helpers import bearer_headers, register_user
from fastapi.testclient import TestClient

from api_platform.api.app import create_app
from api_platform.api.dependencies import AI_PRODUCTION_BLOCKED_DETAIL
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


def _client() -> TestClient:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    return TestClient(create_app(platform=platform))


def _auth_headers(client: TestClient) -> dict[str, str]:
    register_user(client, user_id="copilot-api-user", username="copilotapi")
    return bearer_headers(client, username="copilotapi")


def test_copilot_complete_unauthenticated_401() -> None:
    client = _client()
    response = client.post("/api/v1/copilot/complete", json=_sample_body())
    assert response.status_code == 401


def test_copilot_complete_blocked_without_activation() -> None:
    client = _client()
    headers = _auth_headers(client)
    response = client.post(
        "/api/v1/copilot/complete", headers=headers, json=_sample_body()
    )
    assert response.status_code == 503
    assert response.json()["detail"] == AI_PRODUCTION_BLOCKED_DETAIL


def test_copilot_stream_blocked_without_activation() -> None:
    client = _client()
    headers = _auth_headers(client)
    response = client.post(
        "/api/v1/copilot/stream", headers=headers, json=_sample_body()
    )
    assert response.status_code == 503
    assert "text/event-stream" not in response.headers.get("content-type", "")
    assert response.json()["detail"] == AI_PRODUCTION_BLOCKED_DETAIL


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
    assert {p["id"] for p in data["providers"]} == {
        "openai",
        "anthropic",
        "gemini",
        "deepseek",
    }
