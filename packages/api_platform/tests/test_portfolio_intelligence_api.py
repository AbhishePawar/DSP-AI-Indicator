"""EPIC-A002 Portfolio Intelligence API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.research_object import build_research_object, research_object_to_dict

FIXED = "2026-07-28T12:00:00+00:00"


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


def test_schema(client: TestClient) -> None:
    response = client.get("/api/v1/portfolio/intelligence/schema")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "no_optimisation" in body["schema"]["rules"]


def test_evaluate(client: TestClient) -> None:
    ro = research_object_to_dict(
        build_research_object(
            symbol="AAPL",
            object_id="ro-api-pf",
            created_at=FIXED,
            analysis_payload={
                "ok": True,
                "recommendation_summary": {
                    "label": "Research Mode",
                    "margin_of_safety": 0.1,
                },
            },
        )
    )
    response = client.post(
        "/api/v1/portfolio/intelligence",
        json={
            "portfolio": {
                "portfolio_id": "pf-api",
                "holdings": [{"symbol": "AAPL", "weight": 1.0}],
            },
            "research_objects": {"AAPL": ro},
            "result_id": "pi-api-1",
            "created_at": FIXED,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["portfolio_summary"]["linked_research_count"] == 1
    assert body["result"]["provenance"]["engines_called"] is False


def test_requires_portfolio_or_watchlist(client: TestClient) -> None:
    response = client.post("/api/v1/portfolio/intelligence", json={})
    assert response.status_code == 400
