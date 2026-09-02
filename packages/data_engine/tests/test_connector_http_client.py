"""UrllibJsonHttpClient request-building and fail-closed mapping (no network)."""

from __future__ import annotations

from io import BytesIO
from urllib.error import HTTPError
from urllib.request import Request

import pytest

import data_engine.connector_framework.http as http_mod
from data_engine.connector_framework.http import (
    UrllibJsonHttpClient,
    application_user_agent,
)
from data_engine.exceptions import ProviderRequestError


class _FakeResponse:
    def __init__(self, body: bytes = b'{"ok": true}') -> None:
        self._body = body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._body


def _capture_urlopen(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    captured: dict[str, object] = {}

    def fake_urlopen(request: Request, timeout: float) -> _FakeResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        captured["headers"] = {k.lower(): v for k, v in request.header_items()}
        return _FakeResponse()

    monkeypatch.setattr(http_mod, "urlopen", fake_urlopen)
    return captured


def test_sends_explicit_dsp_user_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DSP_APP_VERSION", raising=False)
    monkeypatch.delenv("DSP_SERVICE_VERSION", raising=False)
    captured = _capture_urlopen(monkeypatch)
    UrllibJsonHttpClient().get_json(
        "https://example.test/v2/instruments/search",
        params={"query": "TCS", "exchanges": "NSE"},
        headers={"Accept": "application/json", "Authorization": "Bearer tok"},
    )
    headers = captured["headers"]
    assert isinstance(headers, dict)
    ua = str(headers.get("user-agent") or "")
    assert ua == application_user_agent()
    assert ua.startswith("DSP-AI-Indicator/")
    assert "Python-urllib" not in ua
    assert "Mozilla" not in ua


def test_user_agent_uses_env_application_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_APP_VERSION", "9.9.9-test")
    captured = _capture_urlopen(monkeypatch)
    UrllibJsonHttpClient().get_json("https://example.test/x")
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers.get("user-agent") == "DSP-AI-Indicator/9.9.9-test"


def test_authorization_and_accept_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_urlopen(monkeypatch)
    token = "must-not-alter-this-token"
    UrllibJsonHttpClient().get_json(
        "https://example.test/x",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers.get("authorization") == f"Bearer {token}"
    assert headers.get("accept") == "application/json"


def test_caller_headers_override_default_and_implicit_user_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_urlopen(monkeypatch)
    client = UrllibJsonHttpClient(
        default_headers={"User-Agent": "default-ua", "X-Default": "d"}
    )
    client.get_json(
        "https://example.test/x",
        headers={"User-Agent": "caller-ua", "X-Caller": "c"},
    )
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers.get("user-agent") == "caller-ua"
    assert headers.get("x-default") == "d"
    assert headers.get("x-caller") == "c"


def test_default_headers_override_implicit_user_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_urlopen(monkeypatch)
    client = UrllibJsonHttpClient(default_headers={"User-Agent": "sec-required-ua"})
    client.get_json("https://example.test/x")
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers.get("user-agent") == "sec-required-ua"


def test_timeout_and_get_method_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_urlopen(monkeypatch)
    UrllibJsonHttpClient(timeout_seconds=15.0).get_json("https://example.test/x")
    assert captured["timeout"] == 15.0
    request = captured["request"]
    assert isinstance(request, Request)
    assert request.get_method() == "GET"


@pytest.mark.parametrize(
    "code,fragment",
    [
        (401, "401 authentication failed"),
        (403, "403 authentication failed"),
    ],
)
def test_auth_errors_fail_closed_without_body_or_token(
    monkeypatch: pytest.MonkeyPatch, code: int, fragment: str
) -> None:
    secret = "super-secret-http-token"

    def _boom(request: Request, timeout: float) -> _FakeResponse:
        raise HTTPError(
            "https://api.upstox.com/v2/instruments/search",
            code,
            "Forbidden",
            hdrs=None,  # type: ignore[arg-type]
            fp=BytesIO(b'{"status":"error","message":"' + secret.encode() + b'"}'),
        )

    monkeypatch.setattr(http_mod, "urlopen", _boom)
    client = UrllibJsonHttpClient(timeout_seconds=1.0)
    with pytest.raises(ProviderRequestError, match=fragment) as excinfo:
        client.get_json(
            "https://api.upstox.com/v2/instruments/search",
            headers={"Authorization": f"Bearer {secret}", "Accept": "application/json"},
        )
    message = str(excinfo.value)
    assert secret not in message
    assert "Bearer" not in message
    assert "Python-urllib" not in message
