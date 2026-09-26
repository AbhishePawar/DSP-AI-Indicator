"""Production website origin and same-origin CORS allow-list."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api_platform.api.app import create_app

CANONICAL_ORIGIN = "https://dspaiindicator.com"
FORMER_CLOUD_RUN_WEB_ORIGIN = "https://dsp-ai-indicator-web-6uxsluxowq-el.a.run.app"
INCORRECT_ORIGINS = (
    "https://dspaindicator.com",
    "https://www.dspaindicator.com",
    FORMER_CLOUD_RUN_WEB_ORIGIN,
)
PRODUCTION_CORS = CANONICAL_ORIGIN
REPO_ROOT = Path(__file__).resolve().parents[3]


def test_production_env_example_is_same_origin_and_not_cloud_run() -> None:
    text = (REPO_ROOT / ".env.production.example").read_text(encoding="utf-8")
    assert "dspaindicator.com" not in text
    assert "run.app" not in text
    assert "DSP_CORS_ORIGINS=https://dspaiindicator.com" in text
    assert "NEXT_PUBLIC_API_BASE_URL=https://dspaiindicator.com/api/v1" in text
    assert not (REPO_ROOT / "cloudbuild.yaml").exists()


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
