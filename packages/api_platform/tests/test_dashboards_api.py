"""API tests — RC1 Milestone 6 enterprise dashboards."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration

ROLES = [
    "research",
    "portfolio-manager",
    "wealth-advisor",
    "family-office",
    "executive",
]


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
    response = client.get("/api/v1/dashboards/schema")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert set(body["schema"]["roles"]) == set(ROLES)


@pytest.mark.parametrize("role", ROLES)
def test_role_endpoint(client: TestClient, role: str) -> None:
    response = client.get(f"/api/v1/dashboards/{role}")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["role"] == role
    assert body["result"]["widgets"]


def test_root_alias(client: TestClient) -> None:
    response = client.get("/dashboards/executive")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_research_with_symbols_query(client: TestClient) -> None:
    response = client.get("/api/v1/dashboards/research?symbols=AAPL,MSFT")
    assert response.status_code == 200
    widgets = response.json()["result"]["widgets"]
    assert "recent_news" in widgets
    assert "watchlist" in widgets
