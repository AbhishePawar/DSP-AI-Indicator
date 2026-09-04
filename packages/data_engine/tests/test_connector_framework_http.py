"""Tests for shared ``UrllibJsonHttpClient`` request construction.

Never opens a network socket: ``urlopen`` is monkeypatched so tests can
inspect the ``urllib.request.Request`` (User-Agent, Authorization, Accept,
URL) in isolation.
"""

from __future__ import annotations

from urllib.request import Request

import pytest

import data_engine.connector_framework.http as http_module
from data_engine.connector_framework.http import UrllibJsonHttpClient


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._body


def _capture_urlopen(monkeypatch: pytest.MonkeyPatch) -> list[Request]:
    captured: list[Request] = []

    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        captured.append(request)
        return _FakeResponse(b'{"ok": true}')

    monkeypatch.setattr(http_module, "urlopen", fake_urlopen)
    return captured


def test_default_user_agent_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_urlopen(monkeypatch)
    client = UrllibJsonHttpClient()
    result = client.get_json("https://example.test/path")

    assert result == {"ok": True}
    assert len(captured) == 1
    request = captured[0]
    assert request.get_header("User-agent") == "dsp-ai-indicator"
    assert request.full_url == "https://example.test/path"


def test_explicit_user_agent_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_urlopen(monkeypatch)
    client = UrllibJsonHttpClient()
    client.get_json(
        "https://example.test/path",
        headers={"User-Agent": "Mozilla/5.0 (dsp-data-engine)"},
    )

    assert captured[0].get_header("User-agent") == "Mozilla/5.0 (dsp-data-engine)"


def test_explicit_user_agent_case_insensitive_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_urlopen(monkeypatch)
    client = UrllibJsonHttpClient()
    client.get_json(
        "https://example.test/path",
        headers={"user-agent": "sec-required-agent"},
    )

    assert captured[0].get_header("User-agent") == "sec-required-agent"


def test_default_headers_user_agent_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_urlopen(monkeypatch)
    client = UrllibJsonHttpClient(
        default_headers={"User-Agent": "Mozilla/5.0 (dsp-data-engine)"}
    )
    client.get_json("https://example.test/path")

    assert captured[0].get_header("User-agent") == "Mozilla/5.0 (dsp-data-engine)"


def test_authorization_and_accept_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_urlopen(monkeypatch)
    client = UrllibJsonHttpClient()
    client.get_json(
        "https://example.test/path",
        headers={
            "Accept": "application/json",
            "Authorization": "Bearer test-token-not-a-secret",
        },
    )

    request = captured[0]
    assert request.get_header("User-agent") == "dsp-ai-indicator"
    assert request.get_header("Accept") == "application/json"
    assert request.get_header("Authorization") == "Bearer test-token-not-a-secret"


def test_url_and_query_construction_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_urlopen(monkeypatch)
    client = UrllibJsonHttpClient(timeout_seconds=15.0)
    client.get_json(
        "https://api.upstox.com/v2/instruments/search",
        params={
            "query": "TCS",
            "exchanges": "NSE,BSE",
            "segments": "EQ",
            "page_number": "1",
            "records": "30",
        },
        headers={
            "Accept": "application/json",
            "Authorization": "Bearer test-token-not-a-secret",
        },
    )

    request = captured[0]
    assert request.full_url == (
        "https://api.upstox.com/v2/instruments/search"
        "?query=TCS&exchanges=NSE%2CBSE&segments=EQ&page_number=1&records=30"
    )
    assert request.get_method() == "GET"
    assert request.get_header("User-agent") == "dsp-ai-indicator"
    assert request.get_header("Accept") == "application/json"
    assert request.get_header("Authorization") == "Bearer test-token-not-a-secret"
