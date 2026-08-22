"""Production website origin, CORS allow-list, and Cloud Build domain config."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api_platform.api.app import create_app

CANONICAL_ORIGIN = "https://dspaiindicator.com"
CLOUD_RUN_WEB_ORIGIN = "https://dsp-ai-indicator-web-6uxsluxowq-el.a.run.app"
INCORRECT_ORIGINS = (
    "https://dspaindicator.com",
    "https://www.dspaindicator.com",
)
PRODUCTION_CORS = f"{CANONICAL_ORIGIN},{CLOUD_RUN_WEB_ORIGIN}"
REPO_ROOT = Path(__file__).resolve().parents[3]


def _deploy_env_vars(text: str) -> dict[str, str]:
    marker = "--update-env-vars="
    for raw_line in text.splitlines():
        idx = raw_line.find(marker)
        if idx < 0:
            continue
        payload = raw_line[idx + len(marker) :].strip()
        if not payload.startswith("^"):
            raise AssertionError("DSP_CORS_ORIGINS deploy args must use ^DELIM^ syntax")
        delim_end = payload.find("^", 1)
        if delim_end < 0:
            raise AssertionError("Cloud Build env-var delimiter is incomplete")
        delimiter = payload[1:delim_end]
        rest = payload[delim_end + 1 :]
        out: dict[str, str] = {}
        for pair in rest.split(delimiter):
            key, _, value = pair.partition("=")
            if key:
                out[key] = value
        return out
    raise AssertionError("cloudbuild.yaml is missing --update-env-vars")


def test_cloudbuild_uses_canonical_production_domain_and_cors_delimiter() -> None:
    text = (REPO_ROOT / "cloudbuild.yaml").read_text(encoding="utf-8")
    assert "dspaindicator.com" not in text
    assert "www.dspaindicator.com" not in text
    assert "--set-env-vars=" not in text
    assert "--set-secrets=" not in text
    env = _deploy_env_vars(text)
    assert env["DSP_RESEND_FROM_ADDRESS"] == "noreply@dspaiindicator.com"
    assert env["DSP_FRONTEND_URL"] == CANONICAL_ORIGIN
    origins = [item.strip() for item in env["DSP_CORS_ORIGINS"].split(",") if item.strip()]
    assert origins == [CANONICAL_ORIGIN, CLOUD_RUN_WEB_ORIGIN]
    secrets = [
        line.strip().lstrip("- ").strip()
        for line in text.splitlines()
        if "--update-secrets=" in line
    ]
    assert secrets, "cloudbuild.yaml must keep --update-secrets"
    secret_arg = secrets[0]
    for name in (
        "DSP_DATABASE_URL",
        "DSP_AUTH_JWT_SECRET",
        "DSP_RESEND_API_KEY",
    ):
        assert name in secret_arg
    assert "DSP_MSG91" not in text
    assert "DSP_GOOGLE_CLIENT_ID" in text
    assert "DSP_GOOGLE_CLIENT_SECRET" in text


@pytest.fixture()
def cors_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")
    monkeypatch.setenv("DSP_CORS_ORIGINS", PRODUCTION_CORS)
    app = create_app(enable_security=False)
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("origin", [CANONICAL_ORIGIN, CLOUD_RUN_WEB_ORIGIN])
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
