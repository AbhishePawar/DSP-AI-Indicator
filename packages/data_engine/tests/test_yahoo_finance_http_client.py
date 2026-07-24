"""Tests for ``UrllibJsonHttpClient``.

These exercise the real, default HTTP implementation, but never touch
the network: ``urlopen`` is monkeypatched to return a canned in-memory
response (or raise), so the tests verify this module's own request
building and error-translation logic in isolation.
"""

from urllib.error import URLError

import pytest

import data_engine.adapters.yahoo_finance.http_client as http_client_module
from data_engine.adapters.yahoo_finance.http_client import UrllibJsonHttpClient
from data_engine.exceptions import ProviderRequestError


class _FakeResponse:
    """Minimal stand-in for the context manager ``urlopen`` returns."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._body


def test_get_json_returns_parsed_body(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(url: str, timeout: float) -> _FakeResponse:
        captured["url"] = url
        captured["timeout"] = timeout
        return _FakeResponse(b'{"chart": {"result": [], "error": null}}')

    monkeypatch.setattr(http_client_module, "urlopen", fake_urlopen)
    client = UrllibJsonHttpClient(timeout_seconds=7.5)

    result = client.get_json("https://example.test/chart", params={"a": "1"})

    assert result == {"chart": {"result": [], "error": None}}
    assert captured["url"] == "https://example.test/chart?a=1"
    assert captured["timeout"] == 7.5


def test_get_json_without_params_omits_query_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(url: str, timeout: float) -> _FakeResponse:
        captured["url"] = url
        return _FakeResponse(b"{}")

    monkeypatch.setattr(http_client_module, "urlopen", fake_urlopen)
    client = UrllibJsonHttpClient()

    client.get_json("https://example.test/chart")

    assert captured["url"] == "https://example.test/chart"


def test_transport_failure_raises_provider_request_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(url: str, timeout: float) -> _FakeResponse:
        raise URLError("connection refused")

    monkeypatch.setattr(http_client_module, "urlopen", fake_urlopen)
    client = UrllibJsonHttpClient()

    with pytest.raises(ProviderRequestError):
        client.get_json("https://example.test/chart")


def test_timeout_raises_provider_request_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(url: str, timeout: float) -> _FakeResponse:
        raise TimeoutError("timed out")

    monkeypatch.setattr(http_client_module, "urlopen", fake_urlopen)
    client = UrllibJsonHttpClient()

    with pytest.raises(ProviderRequestError):
        client.get_json("https://example.test/chart")


def test_invalid_json_body_raises_provider_request_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(url: str, timeout: float) -> _FakeResponse:
        return _FakeResponse(b"not json at all")

    monkeypatch.setattr(http_client_module, "urlopen", fake_urlopen)
    client = UrllibJsonHttpClient()

    with pytest.raises(ProviderRequestError):
        client.get_json("https://example.test/chart")
