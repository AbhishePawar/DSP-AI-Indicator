"""EPIC-A005 Institutional Committee API tests + A004 regression."""

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


def test_schema_and_agents(client: TestClient) -> None:
    schema = client.get("/api/v1/committee/schema")
    assert schema.status_code == 200
    body = schema.json()
    assert body["ok"] is True
    assert "no_scoring" in body["schema"]["rules"]
    assert "buffett" in body["schema"]["agents"]

    agents = client.get("/api/v1/committee/agents")
    assert agents.status_code == 200
    ids = [a["agent_id"] for a in agents.json()["agents"]]
    assert ids[0] == "buffett"
    assert ids[-1] == "devils_advocate"


def test_run_committee(client: TestClient) -> None:
    ro = research_object_to_dict(
        build_research_object(
            symbol="AAPL",
            object_id="ro-api-ic",
            created_at=FIXED,
            analysis_payload={
                "ok": True,
                "recommendation_summary": {
                    "label": "Research Mode",
                    "margin_of_safety": 0.1,
                },
                "risk": {"overall": "moderate"},
            },
        )
    )
    response = client.post(
        "/api/v1/committee/run",
        json={
            "subject": "AAPL",
            "research_object": ro,
            "report_id": "ic-api-1",
            "created_at": FIXED,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert len(body["result"]["reviews"]) == 8
    assert body["result"]["provenance"]["engines_called"] is False


def test_requires_subject(client: TestClient) -> None:
    response = client.post("/api/v1/committee/run", json={"subject": ""})
    assert response.status_code in {400, 422}


def test_a004_regression(client: TestClient) -> None:
    response = client.get("/api/v1/decision/workspace/schema")
    assert response.status_code == 200
    assert response.json()["ok"] is True
