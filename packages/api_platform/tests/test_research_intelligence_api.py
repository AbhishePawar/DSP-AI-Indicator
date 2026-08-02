"""EPIC-011B Research Intelligence API contract tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.research_intelligence import (
    InMemoryResearchSnapshotStore,
    ResearchIntelligenceService,
    reset_research_intelligence_for_tests,
)

FIXED = "2026-08-02T12:00:00+00:00"


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_research_intelligence_for_tests(
        ResearchIntelligenceService(store=InMemoryResearchSnapshotStore())
    )
    yield
    reset_research_intelligence_for_tests(None)


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


def _capture_body(research_id: str = "ri-api-1") -> dict:
    return {
        "research_id": research_id,
        "timestamp": FIXED,
        "ticker": "AAPL",
        "company": "Apple Inc",
        "exchange": "NASDAQ",
        "payload": {
            "symbol": "AAPL",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "price": 100.0,
            "intrinsic_value": 120.0,
            "margin_of_safety": 0.2,
            "investment_recommendation": {
                "decision": "Buy",
                "confidence": 0.8,
            },
            "explainability": {"summary": "Fixture capture"},
            "research_version": "1.0.0",
            "model_version": "m-test",
        },
    }


def test_schema(client: TestClient) -> None:
    response = client.get("/api/v1/research/intelligence/schema")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["schema"]["measurement_only"] is True
    assert "immutable_snapshots" in body["schema"]["rules"]
    assert 12 in body["schema"]["windows_months"]


def test_capture_list_timeline(client: TestClient) -> None:
    cap = client.post("/api/v1/research/intelligence/snapshots", json=_capture_body())
    assert cap.status_code == 200
    body = cap.json()
    assert body["ok"] is True
    assert body["snapshot"]["research_id"] == "ri-api-1"
    assert body["snapshot"]["recommendation"] == "Buy"

    listed = client.get("/api/v1/research/intelligence/snapshots?symbol=AAPL")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    timeline = client.get("/api/v1/research/intelligence/timeline?symbol=AAPL")
    assert timeline.status_code == 200
    assert len(timeline.json()["timeline"]) == 1
    assert timeline.json()["provenance"]["engines_called"] is False


def test_outcome_calibration_performance_insights(client: TestClient) -> None:
    assert (
        client.post(
            "/api/v1/research/intelligence/snapshots", json=_capture_body("ri-api-2")
        ).status_code
        == 200
    )
    out = client.post(
        "/api/v1/research/intelligence/outcomes",
        json={
            "research_id": "ri-api-2",
            "window_months": 12,
            "price_at_horizon": 110.0,
            "measured_at": FIXED,
        },
    )
    assert out.status_code == 200
    outcome = out.json()["outcome"]
    assert outcome["recommendation_accuracy"] == "correct"
    assert outcome["message"] is None

    missing = client.post(
        "/api/v1/research/intelligence/outcomes",
        json={
            "research_id": "ri-api-2",
            "window_months": 24,
            "measured_at": FIXED,
        },
    )
    assert missing.status_code == 200
    assert missing.json()["outcome"]["message"] == "Data unavailable."

    cal = client.post(
        "/api/v1/research/intelligence/calibration",
        json={
            "window_months": 12,
            "horizon_prices": {"ri-api-2": 110.0},
            "result_id": "cal-api",
            "created_at": FIXED,
            "measured_at": FIXED,
        },
    )
    assert cal.status_code == 200
    assert cal.json()["calibration"]["sample_size"] == 1

    perf = client.post(
        "/api/v1/research/intelligence/performance",
        json={
            "window_months": 12,
            "horizon_prices": {"ri-api-2": 110.0},
            "result_id": "dash-api",
            "created_at": FIXED,
            "measured_at": FIXED,
        },
    )
    assert perf.status_code == 200
    assert perf.json()["dashboard"]["overall_accuracy"] == 1.0
    assert perf.json()["dashboard"]["provenance"]["engines_called"] is False

    insights = client.get("/api/v1/research/intelligence/insights?window_months=12")
    assert insights.status_code == 200
    # Without horizon prices on GET, insights may be unavailable — honest
    assert insights.json()["ok"] is True


def test_immutability_via_api(client: TestClient) -> None:
    assert (
        client.post(
            "/api/v1/research/intelligence/snapshots", json=_capture_body("ri-dup")
        ).status_code
        == 200
    )
    dup = client.post(
        "/api/v1/research/intelligence/snapshots",
        json={**_capture_body("ri-dup"), "allow_duplicate": False},
    )
    assert dup.status_code == 400
