"""EPIC-A004 Decision Workspace API tests + A003 regression."""

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
    response = client.get("/api/v1/decision/workspace/schema")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "no_calculations" in body["schema"]["rules"]
    assert "company" in body["schema"]["kinds"]


def test_build_workspace(client: TestClient) -> None:
    ro = research_object_to_dict(
        build_research_object(
            symbol="AAPL",
            object_id="ro-api-ws",
            created_at=FIXED,
            analysis_payload={
                "ok": True,
                "recommendation_summary": {"label": "Research Mode"},
            },
        )
    )
    response = client.post(
        "/api/v1/decision/workspace",
        json={
            "kind": "company",
            "subject": "AAPL",
            "research_object": ro,
            "monitoring_result": {
                "result_id": "mon-api",
                "created_at": FIXED,
                "alerts": [],
                "audit": {"alert_count": 0},
            },
            "workspace_id": "ws-api-1",
            "created_at": FIXED,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["provenance"]["engines_called"] is False
    assert len(body["result"]["panels"]) == 11


def test_invalid_kind(client: TestClient) -> None:
    response = client.post(
        "/api/v1/decision/workspace",
        json={"kind": "trade", "subject": "AAPL"},
    )
    assert response.status_code == 400


def test_a003_regression(client: TestClient) -> None:
    response = client.get("/api/v1/research/monitoring/schema")
    assert response.status_code == 200
    assert response.json()["ok"] is True
