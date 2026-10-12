"""Unit tests for the Upstox quote adapter; all HTTP is mocked."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime

import pytest

from contracts.domain.instrument import AssetClass, Instrument
from data_engine.exceptions import ProviderRequestError
from data_engine.market_quote.adapters import build_default_quote_adapter_from_env
from data_engine.market_quote.upstox_adapter import (
    UpstoxQuoteAdapter,
    resolve_upstox_instrument_key,
)


def _instrument(
    *, exchange: str = "NSE", isin: str | None = "INE848E01016"
) -> Instrument:
    return Instrument(
        symbol="NHPC",
        asset_class=AssetClass.EQUITY,
        currency="INR",
        exchange=exchange,
        isin=isin,
        country="IN",
    )


class _Response:
    status = 200

    def __init__(self, payload: object) -> None:
        self.body = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_factory_selects_upstox_when_explicitly_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    monkeypatch.setenv("DSP_UPSTOX_ANALYTICS_TOKEN", "test-token-never-real")
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    adapter = build_default_quote_adapter_from_env()
    assert isinstance(adapter, UpstoxQuoteAdapter)
    assert adapter.provider_id == "upstox_market_quote"


def test_factory_fails_closed_if_upstox_token_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from data_engine.connector_framework.production_profile import (
        ConnectorConfigurationError,
    )

    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    for name in (
        "DSP_UPSTOX_ANALYTICS_TOKEN",
        "DSP_UPSTOX_ACCESS_TOKEN",
        "UPSTOX_ACCESS_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(
        ConnectorConfigurationError, match="DSP_UPSTOX_ANALYTICS_TOKEN"
    ):
        build_default_quote_adapter_from_env()


def test_resolves_instrument_only_from_verified_isin_and_exchange() -> None:
    assert (
        resolve_upstox_instrument_key(_instrument())
        == "NSE_EQ|INE848E01016"
    )
    assert (
        resolve_upstox_instrument_key(_instrument(exchange="BSE"))
        == "BSE_EQ|INE848E01016"
    )
    assert resolve_upstox_instrument_key(_instrument(isin=None)) is None
    assert resolve_upstox_instrument_key(_instrument(exchange="NASDAQ")) is None


def test_maps_genuine_quote_fields_and_source_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "status": "success",
        "data": {
            "NSE_EQ:NHPC": {
                "last_price": 73.4,
                "volume": 4112974,
                "average_price": 72.92,
                "timestamp": "2026-10-12T15:45:00+05:30",
                "ohlc": {
                    "open": 72.9,
                    "high": 73.47,
                    "low": 72.15,
                    "close": 73.4,
                },
            }
        },
    }
    captured: dict[str, object] = {}

    def fake_urlopen(
        request: urllib.request.Request, timeout: float
    ) -> _Response:
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["api_version"] = request.get_header("Api-version")
        captured["timeout"] = timeout
        return _Response(payload)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    quote = UpstoxQuoteAdapter(access_token="test-token-never-real").get_quote(
        _instrument()
    )
    assert quote is not None
    assert float(quote.current_price.value) == pytest.approx(73.4)
    assert float(quote.open.value) == pytest.approx(72.9)
    assert float(quote.high.value) == pytest.approx(73.47)
    assert float(quote.low.value) == pytest.approx(72.15)
    assert float(quote.previous_close.value) == pytest.approx(73.4)
    assert float(quote.volume.value) == 4112974
    assert quote.average_volume.available is False
    assert quote.provenance.provider_id == "upstox_market_quote"
    assert quote.provenance.auth_mode == "bearer_token"
    assert quote.provenance.as_of is not None
    assert quote.provenance.as_of.utcoffset() == datetime.fromisoformat(
        "2026-10-12T15:45:00+05:30"
    ).utcoffset()
    assert "instrument_key=NSE_EQ%7CINE848E01016" in str(captured["url"])
    assert captured["authorization"] == "Bearer test-token-never-real"
    assert captured["api_version"] == "3.0"


def test_unresolved_instrument_does_not_call_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *args, **kwargs: pytest.fail("network must not be called"),
    )
    quote = UpstoxQuoteAdapter(access_token="test-token").get_quote(
        _instrument(isin=None)
    )
    assert quote is None


def test_malformed_json_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    class BadResponse(_Response):
        def read(self) -> bytes:
            return b"not-json"

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *args, **kwargs: BadResponse({}),
    )
    with pytest.raises(ProviderRequestError, match="not valid JSON"):
        UpstoxQuoteAdapter(access_token="test-token").get_quote(_instrument())


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (401, "authentication/permission failure"),
        (403, "authentication/permission failure"),
        (429, "rate limit exceeded"),
        (503, "HTTP 503"),
    ],
)
def test_http_errors_are_sanitized_and_never_include_token(
    monkeypatch: pytest.MonkeyPatch, status: int, message: str
) -> None:
    token = "sensitive-test-token"

    def fail_request(*args: object, **kwargs: object) -> None:
        raise urllib.error.HTTPError(
            "https://api.upstox.com/v3/market-quote/quotes",
            status,
            "test error",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(urllib.request, "urlopen", fail_request)
    with pytest.raises(ProviderRequestError, match=message) as error:
        UpstoxQuoteAdapter(access_token=token).get_quote(_instrument())
    assert token not in str(error.value)


def test_timeout_error_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(*args: object, **kwargs: object) -> None:
        raise TimeoutError("socket timeout")

    monkeypatch.setattr(urllib.request, "urlopen", timeout)
    with pytest.raises(ProviderRequestError, match="timed out"):
        UpstoxQuoteAdapter(access_token="sensitive-test-token").get_quote(
            _instrument()
        )


def test_health_does_not_claim_live_connectivity() -> None:
    health = UpstoxQuoteAdapter(access_token="test-token").health()
    assert health.healthy is True
    assert health.authenticated is True
    assert "live connectivity not checked" in health.detail


def test_source_time_parser_handles_epoch_and_iso() -> None:
    from data_engine.market_quote.upstox_adapter import _parse_source_time

    iso = _parse_source_time("2026-10-12T15:45:00+05:30")
    assert iso is not None
    assert iso.utcoffset() == datetime.fromisoformat(
        "2026-10-12T15:45:00+05:30"
    ).utcoffset()
    epoch = _parse_source_time(1791828900000)
    assert epoch is not None
    assert epoch.tzinfo is not None
