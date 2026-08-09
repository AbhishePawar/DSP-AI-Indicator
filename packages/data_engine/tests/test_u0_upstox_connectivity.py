"""U0 — Upstox Analytics Token connectivity (mocked HTTP; no live secrets)."""

from __future__ import annotations

from typing import Any, Mapping

import pytest

from data_engine.connector_framework.http import UrllibJsonHttpClient
from data_engine.exceptions import ProviderRequestError
from data_engine.upstox_connectivity import (
    UPSTOX_ANALYTICS_TOKEN_ENV,
    UPSTOX_CONNECTIVITY_ENDPOINT,
    UpstoxConnectivityClient,
    redact_secret,
    resolve_u0_upstox_analytics_token,
)


class _FakeHttp:
    def __init__(
        self,
        *,
        payload: Any = None,
        error: Exception | None = None,
        capture: list | None = None,
    ) -> None:
        self._payload = payload
        self._error = error
        self.capture = capture if capture is not None else []

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        self.capture.append(
            {"url": url, "params": dict(params or {}), "headers": dict(headers or {})}
        )
        if self._error is not None:
            raise self._error
        return self._payload


def test_token_absent_does_not_crash_and_reports_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(UPSTOX_ANALYTICS_TOKEN_ENV, raising=False)
    monkeypatch.delenv("DSP_UPSTOX_ACCESS_TOKEN", raising=False)
    client = UpstoxConnectivityClient(access_token="")
    status = client.status()
    assert status.configured is False
    assert status.authenticated is False
    assert "DSP_UPSTOX_ANALYTICS_TOKEN" in status.detail
    result = client.probe_market_data()
    assert result.ok is False
    assert result.http_success is False
    assert result.response_shape == {}
    assert "absent" in result.detail.lower() or "missing" in result.detail.lower()


def test_production_absent_token_fail_closed_no_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    client = UpstoxConnectivityClient(access_token="")
    result = client.probe_market_data()
    assert result.ok is False
    assert "fail-closed" in result.detail.lower()
    assert "fixture" in result.detail.lower()


def test_resolve_prefers_canonical_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(UPSTOX_ANALYTICS_TOKEN_ENV, "canonical-token")
    monkeypatch.setenv("DSP_UPSTOX_ACCESS_TOKEN", "legacy-alias")
    assert resolve_u0_upstox_analytics_token() == "canonical-token"


def test_authorization_header_bearer_without_exposing_in_status() -> None:
    secret = "u0-unit-test-token-value"
    client = UpstoxConnectivityClient(access_token=secret)
    headers = client.authorization_headers()
    assert headers["Authorization"] == f"Bearer {secret}"
    assert headers["Accept"] == "application/json"
    status = client.status()
    assert status.configured is True
    assert secret not in status.detail
    assert "Bearer" not in status.detail


def test_probe_success_shape_only(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "u0-success-token"
    capture: list = []
    http = _FakeHttp(
        payload={
            "status": "success",
            "data": {"NSE_INDEX:Nifty 50": {"last_price": 25000.0}},
        },
        capture=capture,
    )
    client = UpstoxConnectivityClient(access_token=secret, http_client=http)
    result = client.probe_market_data()
    assert result.ok is True
    assert result.http_success is True
    assert result.status_code == 200
    assert result.endpoint == UPSTOX_CONNECTIVITY_ENDPOINT
    assert result.endpoint_category == "market_data"
    assert result.provider == "Upstox"
    assert result.latency_ms is not None
    assert result.response_shape["type"] == "object"
    assert "status" in result.response_shape["keys"]
    # Must not embed quote values as investment facts in the connectivity result.
    assert "25000" not in str(result.response_shape)
    assert secret not in result.detail
    assert capture and "Authorization" in capture[0]["headers"]
    assert capture[0]["headers"]["Authorization"] == f"Bearer {secret}"
    assert UPSTOX_CONNECTIVITY_ENDPOINT in capture[0]["url"]


def test_invalid_credential_surfaces_safely() -> None:
    secret = "bad-token-should-not-leak"
    http = _FakeHttp(
        error=ProviderRequestError(
            "HTTP 401 authentication failed for 'https://api.upstox.com/v2/market-quote/ltp'"
        )
    )
    client = UpstoxConnectivityClient(access_token=secret, http_client=http)
    result = client.probe_market_data()
    assert result.ok is False
    assert result.http_success is False
    assert result.status_code == 401
    assert secret not in result.detail
    assert "401" in result.detail


def test_rate_limit_recognized_bounded_retries() -> None:
    secret = "rate-limit-token"
    calls = {"n": 0}

    class _RateLimitHttp:
        def get_json(self, url: str, *, params=None, headers=None):
            calls["n"] += 1
            raise ProviderRequestError(
                "HTTP 429 rate limited for 'https://api.upstox.com/v2/market-quote/ltp'"
            )

    client = UpstoxConnectivityClient(
        access_token=secret,
        http_client=_RateLimitHttp(),  # type: ignore[arg-type]
        max_attempts=2,
    )
    result = client.probe_market_data()
    assert result.ok is False
    assert result.status_code == 429
    assert calls["n"] == 2
    assert secret not in result.detail


def test_https_required_for_upstox_base_url() -> None:
    client = UpstoxConnectivityClient(
        access_token="tok",
        base_url="http://api.upstox.com/v2",
        http_client=_FakeHttp(payload={"status": "success", "data": {}}),
    )
    result = client.probe_market_data()
    assert result.ok is False
    assert "HTTPS" in result.detail


def test_redact_secret_and_error_path() -> None:
    secret = "super-secret-upstox-token"
    assert "***REDACTED***" in redact_secret(f"Bearer {secret} leaked", secret)
    client = UpstoxConnectivityClient(access_token=secret)
    err = client._safe_error(RuntimeError(f"boom {secret}"))
    assert secret not in str(err)


def test_token_not_in_exception_from_auth_headers_when_absent() -> None:
    client = UpstoxConnectivityClient(access_token="")
    with pytest.raises(ProviderRequestError, match="DSP_UPSTOX_ANALYTICS_TOKEN"):
        client.authorization_headers()


def test_urllib_client_maps_429_without_body_leak(monkeypatch: pytest.MonkeyPatch) -> None:
    from urllib.error import HTTPError
    from io import BytesIO

    def _boom(*args, **kwargs):
        raise HTTPError(
            "https://api.upstox.com/v2/x",
            429,
            "Too Many Requests",
            hdrs=None,  # type: ignore[arg-type]
            fp=BytesIO(b"rate"),
        )

    monkeypatch.setattr(
        "data_engine.connector_framework.http.urlopen",
        _boom,
    )
    client = UrllibJsonHttpClient(timeout_seconds=1.0)
    with pytest.raises(ProviderRequestError, match="429 rate limited"):
        client.get_json("https://api.upstox.com/v2/x")


def test_live_upstox_connectivity_optional() -> None:
    """Runs only when DSP_UPSTOX_ANALYTICS_TOKEN is present in the environment."""
    token = resolve_u0_upstox_analytics_token()
    if not token:
        pytest.skip("UPSTOX LIVE TEST = NOT RUN; REASON = CREDENTIAL ABSENT")
    client = UpstoxConnectivityClient()
    result = client.probe_market_data()
    # Never assert token; only connectivity outcome.
    assert result.provider == "Upstox"
    assert result.endpoint_category == "market_data"
    assert result.retrieved_at is not None
    assert token not in result.detail
    assert token not in str(result.response_shape)
    # Live proof: must succeed for this optional test when token is real.
    assert result.ok is True
    assert result.http_success is True
