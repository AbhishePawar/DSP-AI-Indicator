"""Password strength must not accept secrets via GET query string."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import PlatformBuilder, PlatformConfiguration


def test_password_strength_get_rejected() -> None:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(create_app(platform=platform))
    response = client.get(
        "/api/v1/auth/enterprise/password/strength",
        params={"password": "SuperSecret1!"},
    )
    assert response.status_code == 405
    body = response.json()
    assert body.get("ok") is False


def test_password_strength_post_ok() -> None:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(create_app(platform=platform))
    response = client.post(
        "/api/v1/auth/enterprise/password/strength",
        json={"password": "SuperSecret1!"},
    )
    assert response.status_code == 200
    assert response.json().get("ok") is True
