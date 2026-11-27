"""Production VPS website origin and CORS security contracts."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api_platform.api.app import create_app

CANONICAL_ORIGIN = "https://dspaiindicator.com"
INCORRECT_ORIGINS = (
    "https://dspaindicator.com",
    "https://www.dspaindicator.com",
    "https://untrusted.example",
    "https://legacy-service.a.run.app",
)
PRODUCTION_CORS = CANONICAL_ORIGIN
REPO_ROOT = Path(__file__).resolve().parents[3]


def test_vps_production_auth_contract() -> None:
    compose = (
        REPO_ROOT / "docker/docker-compose.production.yml"
    ).read_text(encoding="utf-8")

    template = (
        REPO_ROOT / ".env.production.example"
    ).read_text(encoding="utf-8")

    assert "DSP_ENVIRONMENT: production" in compose
    assert 'DSP_ENABLE_SECURITY: "true"' in compose
    assert 'DSP_REQUIRE_ADMIN_AUTH: "true"' in compose
    assert 'DSP_HSTS_ENABLED: "true"' in compose
    assert "../.env.production" in compose
    assert "DSP_CORS_ORIGINS=" in template
    assert "DSP_DATABASE_URL=" in template
    assert "DSP_JWT_SECRET=" in template
    assert "dspaindicator.com" not in template


@pytest.fixture()
def cors_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")
    monkeypatch.setenv("DSP_CORS_ORIGINS", PRODUCTION_CORS)
    app = create_app(enable_security=False)
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("origin", [CANONICAL_ORIGIN])
def test_production_origins_are_allowed(cors_client: TestClient, origin: str) -> None:
    response = cors_client.get("/health/ready", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin


@pytest.mark.parametrize("origin", INCORRECT_ORIGINS)
def test_incorrect_production_domains_are_rejected(
    cors_client: TestClient, origin: str
) -> None:
    response = cors_client.get("/health/ready", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") != origin
    assert response.headers.get("access-control-allow-origin") is None
