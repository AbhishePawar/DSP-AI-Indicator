"""API + integration tests — RC1 Milestone 7 Copilot 2.0."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.copilot_v2 import reset_copilot_memory_store_for_tests
from dsp_platform.copilot_v2.memory import CopilotMemoryStore


@pytest.fixture
def platform() -> DSPPlatform:
    reset_copilot_memory_store_for_tests(CopilotMemoryStore())
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )


@pytest.fixture
def client(platform: DSPPlatform) -> TestClient:
    return TestClient(create_app(platform=platform))


def test_schema(client: TestClient) -> None:
    response = client.get("/api/v1/copilot/schema")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "company" in body["schema"]["modes"]
    assert "/copilot/document" in body["schema"]["routes"]


def test_chat_company_route(client: TestClient) -> None:
    response = client.post(
        "/api/v1/copilot/company",
        json={"message": "Analyze TCS", "symbols": ["TCS"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["intent"] == "company"
    assert body["result"]["conversation_id"]


def test_portfolio_route(client: TestClient) -> None:
    response = client.post(
        "/api/v1/copilot/portfolio",
        json={"message": "Analyze my portfolio", "symbols": ["AAPL"]},
    )
    assert response.status_code == 200
    assert response.json()["result"]["intent"] == "portfolio"


def test_valuation_route_with_payload(client: TestClient) -> None:
    response = client.post(
        "/api/v1/copilot/valuation",
        json={
            "message": "Explain MoS",
            "analyse_response": {
                "recommendation_summary": {"margin_of_safety": 0.15},
                "valuation": {"intrinsic_value": 250},
            },
        },
    )
    assert response.status_code == 200
    answer = response.json()["result"]["answer"]
    assert "250" in answer


def test_comparison_requires_payloads(client: TestClient) -> None:
    response = client.post(
        "/api/v1/copilot/comparison",
        json={"message": "Compare TCS vs INFY", "symbols": ["TCS", "INFY"]},
    )
    assert response.status_code == 200
    assert response.json()["result"]["unavailable"] is True


def test_document_route(client: TestClient) -> None:
    response = client.post(
        "/api/v1/copilot/document",
        json={"message": "Summarize filings", "symbol": "AAPL", "document_kind": "filings"},
    )
    assert response.status_code == 200
    assert response.json()["result"]["intent"] == "document"


def test_history_list_get_delete(client: TestClient) -> None:
    created = client.post("/api/v1/copilot/chat", json={"message": "hello memory"})
    assert created.status_code == 200
    cid = created.json()["result"]["conversation_id"]

    listed = client.get("/api/v1/copilot/history")
    assert listed.status_code == 200
    assert any(c["conversation_id"] == cid for c in listed.json()["conversations"])

    detail = client.get(f"/api/v1/copilot/history/{cid}")
    assert detail.status_code == 200
    assert detail.json()["result"]["turns"]

    deleted = client.delete(f"/api/v1/copilot/history/{cid}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True

    missing = client.delete(f"/api/v1/copilot/history/{cid}")
    assert missing.status_code == 404


def test_complete_and_stream_fail_closed_without_activation(client: TestClient) -> None:
    body = {
        "question_id": "why_buy",
        "request": {"ticker": "AAPL", "company": "Apple", "exchange": "NASDAQ"},
        "response": {
            "ok": True,
            "payload": {
                "ok": True,
                "recommendation_summary": {
                    "decision": "Buy",
                    "confidence": 0.8,
                    "margin_of_safety": 0.2,
                },
            },
        },
    }
    complete = client.post("/api/v1/copilot/complete", json=body)
    assert complete.status_code == 401
    stream = client.post("/api/v1/copilot/stream", json=body)
    assert stream.status_code == 401
