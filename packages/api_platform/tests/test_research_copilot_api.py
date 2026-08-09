"""EPIC-A001 AI Research Copilot API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from auth_test_helpers import bearer_headers, register_user
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.research_copilot import (
    ConversationStore,
    reset_conversation_store_for_tests,
)
from dsp_platform.research_object import build_research_object, research_object_to_dict

FIXED = "2026-07-28T12:00:00+00:00"


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_conversation_store_for_tests(ConversationStore())
    yield
    reset_conversation_store_for_tests(None)


@pytest.fixture
def platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .build()
    )


@pytest.fixture
def client(platform: DSPPlatform) -> TestClient:
    return TestClient(create_app(platform=platform))

@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    register_user(client, user_id="research-cop-user", username="researchcop")
    return bearer_headers(client, username="researchcop")


def test_copilot_schema(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/research/copilot/schema")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["schema"]["mode"] == "extractive_grounded"
    assert "no_provider_calls" in body["schema"]["rules"]


def test_copilot_ask(client: TestClient, auth_headers: dict[str, str]) -> None:
    ro = research_object_to_dict(
        build_research_object(
            symbol="AAPL",
            object_id="ro-api-c",
            created_at=FIXED,
            analysis_payload={
                "ok": True,
                "recommendation_summary": {"label": "Research Mode"},
            },
        )
    )
    response = client.post(
        "/api/v1/research/copilot/ask",
        headers=auth_headers,
        json={
            "question": "What is the recommendation?",
            "research_object": ro,
            "response_id": "api-resp-1",
            "created_at": FIXED,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["response"]["citations"]
    assert body["response"]["provenance"]["providers_called"] is False


def test_copilot_ask_no_context(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/research/copilot/ask",
        headers=auth_headers,
        json={"question": "What is the price?", "created_at": FIXED},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["response"]["unavailable"] is True
    assert body["response"]["answer"] == "Data unavailable."
