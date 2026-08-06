"""EPIC-A006 Investment Policy API tests + A005 regression."""

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


def test_schema_and_default(client: TestClient) -> None:
    schema = client.get("/api/v1/policy/schema")
    assert schema.status_code == 200
    body = schema.json()
    assert body["ok"] is True
    assert "no_scoring" in body["schema"]["rules"]
    assert "require_section_available" in body["schema"]["rule_kinds"]

    default = client.get("/api/v1/policy/default")
    assert default.status_code == 200
    assert default.json()["policy"]["policy_id"]


def test_evaluate(client: TestClient) -> None:
    ro = research_object_to_dict(
        build_research_object(
            symbol="AAPL",
            object_id="ro-api-pol",
            created_at=FIXED,
            analysis_payload={
                "ok": True,
                "recommendation_summary": {
                    "label": "Research Mode",
                    "margin_of_safety": 0.2,
                },
                "risk": {"overall": "moderate"},
            },
        )
    )
    response = client.post(
        "/api/v1/policy/evaluate",
        json={
            "subject": "AAPL",
            "research_object": ro,
            "committee_report": {
                "report_id": "ic-api",
                "consensus": {"stance": "supportive"},
            },
            "portfolio_intelligence": {
                "result_id": "pi-api",
                "missing_research": [],
            },
            "result_id": "pol-api-1",
            "created_at": FIXED,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["provenance"]["engines_called"] is False
    assert body["result"]["summary"]["status"]


def test_a005_regression(client: TestClient) -> None:
    response = client.get("/api/v1/committee/schema")
    assert response.status_code == 200
    assert response.json()["ok"] is True
