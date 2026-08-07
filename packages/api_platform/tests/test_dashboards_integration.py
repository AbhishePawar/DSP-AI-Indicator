"""Integration tests — RC1 Milestone 6 dashboards across engines."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration


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


def test_portfolio_manager_reuses_pi_missing_research(client: TestClient) -> None:
    response = client.get(
        "/api/v1/dashboards/portfolio-manager",
        params={"portfolio_id": "pf-int-1", "symbols": "AAPL,MSFT"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    health = body["result"]["widgets"]["portfolio_health_score"]
    assert health["available"] is True
    assert health["data"]["missing_research_count"] == 2
    assert health["data"]["health_score"] == "Data unavailable."
    assert body["result"]["provenance"]["calculations_performed"] is False


def test_executive_includes_system_health_or_unavailable(client: TestClient) -> None:
    response = client.get("/api/v1/dashboards/executive")
    assert response.status_code == 200
    widgets = response.json()["result"]["widgets"]
    assert "system_health" in widgets
    assert "platform_kpis" in widgets
    # Health probe may pass or honestly mark unavailable — never invent KPIs
    assert widgets["system_health"]["message"] in (None, "Data unavailable.")


def test_wealth_advisor_workflow_unavailable_without_id(client: TestClient) -> None:
    response = client.get("/api/v1/dashboards/wealth-advisor")
    assert response.status_code == 200
    widgets = response.json()["result"]["widgets"]
    assert widgets["recommended_actions"]["available"] is False
    assert widgets["recommended_actions"]["message"] == "Data unavailable."
