"""U2 — Upstox authenticated market quote via U1 identity (mocked HTTP)."""

from __future__ import annotations

from typing import Any, Mapping

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.exceptions import ProviderRequestError
from data_engine.upstox_investment import UpstoxQuoteAdapter
from data_engine.upstox_market_quote import (
    UPSTOX_MARKET_QUOTE_ENDPOINT,
    UpstoxMarketQuoteClient,
    UpstoxMarketQuoteRequest,
)


def _eq(
    *,
    symbol: str,
    name: str,
    exchange: str,
    isin: str,
) -> dict[str, Any]:
    return {
        "segment": f"{exchange}_EQ",
        "name": name,
        "exchange": exchange,
        "isin": isin,
        "instrument_type": "EQ",
        "instrument_key": f"{exchange}_EQ|{isin}",
        "trading_symbol": symbol,
        "short_name": symbol,
    }


def _quote_row(*, symbol: str, price: float, key: str) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {
            key: {
                "ohlc": {"open": price - 1, "high": price + 1, "low": price - 2, "close": price - 0.5},
                "timestamp": "2026-08-09T10:00:00+05:30",
                "symbol": symbol,
                "last_price": price,
                "volume": 1000,
                "average_price": price,
            }
        },
    }


class _FakeHttp:
    def __init__(self, *, search: Mapping[str, Any], quotes: Mapping[str, Any] | None = None, error_on: str | None = None, error: Exception | None = None) -> None:
        self.search = dict(search)
        self.quotes = dict(quotes or {})
        self.error_on = error_on
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def get_json(self, url: str, *, params=None, headers=None):
        self.calls.append({"url": url, "params": dict(params or {}), "headers": dict(headers or {})})
        assert headers and str(headers.get("Authorization", "")).startswith("Bearer ")
        if self.error is not None and (
            self.error_on is None
            or self.error_on in url
        ):
            raise self.error
        if "instruments/search" in url:
            q = str((params or {}).get("query") or "").upper()
            return self.search.get(q, {"status": "success", "data": []})
        if UPSTOX_MARKET_QUOTE_ENDPOINT in url:
            key = str((params or {}).get("instrument_key") or "")
            if key in self.quotes:
                return self.quotes[key]
            # default empty
            return {"status": "success", "data": {}}
        raise AssertionError(url)


_INFY = _eq(symbol="INFY", name="Infosys Limited", exchange="NSE", isin="INE009A01021")
_TCS_NSE = _eq(symbol="TCS", name="Tata Consultancy Services Limited", exchange="NSE", isin="INE467B01029")
_TCS_BSE = _eq(symbol="TCS", name="Tata Consultancy Services Limited", exchange="BSE", isin="INE467B01029")


def _client_for(
    *,
    search_rows: list[dict[str, Any]],
    symbol: str,
    price: float = 1500.0,
    quote_payload: dict[str, Any] | None = None,
    error_on: str | None = None,
    error: Exception | None = None,
) -> UpstoxMarketQuoteClient:
    key = search_rows[0]["instrument_key"] if len(search_rows) == 1 else ""
    quotes = {}
    if len(search_rows) == 1:
        quotes[key] = quote_payload or _quote_row(symbol=symbol, price=price, key=key)
    http = _FakeHttp(
        search={symbol: {"status": "success", "data": search_rows}},
        quotes=quotes,
        error_on=error_on,
        error=error,
    )
    return UpstoxMarketQuoteClient(access_token="u2-test-token", http_client=http)


def test_infy_u1_then_quote() -> None:
    client = _client_for(search_rows=[_INFY], symbol="INFY", price=1610.25)
    result = client.get_quote("INFY")
    assert result.status == "OK"
    assert result.identity is not None
    assert result.identity.isin == "INE009A01021"
    assert result.quote is not None
    assert result.quote.symbol == "INFY"
    assert result.quote.exchange == "NSE"
    assert result.quote.currency == "INR"
    assert float(result.quote.current_price.value) == pytest.approx(1610.25)
    assert result.quote.provenance.provider_id == "upstox_market_quote"
    assert result.quote.provenance.auth_mode == "bearer_token"
    assert result.quote.provenance.metadata["u1_resolution"] == "RESOLVED"
    assert result.retrieved_at is not None


def test_tcs_ambiguous_does_not_guess_quote() -> None:
    http = _FakeHttp(
        search={"TCS": {"status": "success", "data": [_TCS_NSE, _TCS_BSE]}},
        quotes={},
    )
    client = UpstoxMarketQuoteClient(access_token="tok", http_client=http)
    result = client.get_quote("TCS")
    assert result.status == "AMBIGUOUS"
    assert result.quote is None
    # Must not have called market-quote when unresolved.
    assert not any(UPSTOX_MARKET_QUOTE_ENDPOINT in c["url"] for c in http.calls)


def test_tcs_preferred_nse_quotes() -> None:
    key = _TCS_NSE["instrument_key"]
    http = _FakeHttp(
        search={"TCS": {"status": "success", "data": [_TCS_NSE, _TCS_BSE]}},
        quotes={key: _quote_row(symbol="TCS", price=4200.0, key=key)},
    )
    client = UpstoxMarketQuoteClient(access_token="tok", http_client=http)
    result = client.get_quote(
        UpstoxMarketQuoteRequest(symbol="TCS", preferred_exchange="NSE")
    )
    assert result.status == "OK"
    assert result.identity is not None
    assert result.identity.exchange == "NSE"
    assert result.quote is not None
    assert float(result.quote.current_price.value) == pytest.approx(4200.0)
    assert any(
        c["params"].get("instrument_key") == key for c in http.calls if UPSTOX_MARKET_QUOTE_ENDPOINT in c["url"]
    )


def test_client_instrument_key_rejected() -> None:
    client = _client_for(search_rows=[_INFY], symbol="INFY")
    result = client.get_quote(
        UpstoxMarketQuoteRequest(
            symbol="INFY", client_instrument_key="NSE_EQ|INE009A01021"
        )
    )
    assert result.status == "REJECTED"
    assert result.quote is None


def test_client_price_rejected() -> None:
    client = _client_for(search_rows=[_INFY], symbol="INFY")
    result = client.get_quote(
        UpstoxMarketQuoteRequest(symbol="INFY", client_price=1.0)
    )
    assert result.status == "REJECTED"


def test_missing_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DSP_UPSTOX_ANALYTICS_TOKEN", raising=False)
    monkeypatch.delenv("DSP_UPSTOX_ACCESS_TOKEN", raising=False)
    client = UpstoxMarketQuoteClient(access_token="")
    result = client.get_quote("INFY")
    assert result.status == "UNAVAILABLE"


def test_production_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    client = UpstoxMarketQuoteClient(access_token="")
    result = client.get_quote("INFY")
    assert result.status == "UNAVAILABLE"
    assert "fail-closed" in result.detail.lower()


@pytest.mark.parametrize(
    "code,fragment",
    [
        (401, "401 authentication failed"),
        (403, "403 authentication failed"),
        (404, "404"),
        (429, "429 rate limited"),
    ],
)
def test_http_errors(code: int, fragment: str) -> None:
    secret = "secret-u2"
    http = _FakeHttp(
        search={"INFY": {"status": "success", "data": [_INFY]}},
        quotes={},
        error_on=UPSTOX_MARKET_QUOTE_ENDPOINT,
        error=ProviderRequestError(
            f"HTTP {fragment} for 'https://api.upstox.com/v2/{UPSTOX_MARKET_QUOTE_ENDPOINT}'"
        ),
    )
    client = UpstoxMarketQuoteClient(access_token=secret, http_client=http, max_attempts=2)
    result = client.get_quote("INFY")
    assert result.status == "UNAVAILABLE"
    assert result.http_status == code
    assert secret not in result.detail
    if code == 429:
        assert sum(1 for c in http.calls if UPSTOX_MARKET_QUOTE_ENDPOINT in c["url"]) == 2


def test_timeout_unavailable() -> None:
    http = _FakeHttp(
        search={"INFY": {"status": "success", "data": [_INFY]}},
        error_on=UPSTOX_MARKET_QUOTE_ENDPOINT,
        error=ProviderRequestError(
            "HTTP request to 'https://api.upstox.com/v2/market-quote/quotes' failed: TimeoutError"
        ),
    )
    client = UpstoxMarketQuoteClient(access_token="tok", http_client=http)
    result = client.get_quote("INFY")
    assert result.status == "UNAVAILABLE"


def test_malformed_quote_response() -> None:
    key = _INFY["instrument_key"]
    client = _client_for(
        search_rows=[_INFY],
        symbol="INFY",
        quote_payload={"status": "success", "data": "nope"},
    )
    # override quotes via reconstructing — malformed data mapping
    http = _FakeHttp(
        search={"INFY": {"status": "success", "data": [_INFY]}},
        quotes={key: {"status": "success", "data": []}},
    )
    client = UpstoxMarketQuoteClient(access_token="tok", http_client=http)
    result = client.get_quote("INFY")
    assert result.status == "UNAVAILABLE"


def test_missing_price_unavailable() -> None:
    key = _INFY["instrument_key"]
    payload = {
        "status": "success",
        "data": {
            key: {
                "ohlc": {"open": 1, "high": 1, "low": 1, "close": 1},
                "symbol": "INFY",
                "last_price": None,
            }
        },
    }
    client = _client_for(search_rows=[_INFY], symbol="INFY", quote_payload=payload)
    result = client.get_quote("INFY")
    assert result.status == "UNAVAILABLE"
    assert "price" in result.detail.lower()


def test_adapter_uses_u1_no_silent_nse_on_ambiguous() -> None:
    http = _FakeHttp(
        search={"TCS": {"status": "success", "data": [_TCS_NSE, _TCS_BSE]}},
        quotes={},
    )
    adapter = UpstoxQuoteAdapter(access_token="tok", http_client=http)
    quote = adapter.get_quote(
        Instrument(symbol="TCS", asset_class=AssetClass.EQUITY, currency="INR")
    )
    assert quote is None


def test_adapter_resolves_with_exchange_on_instrument() -> None:
    key = _TCS_NSE["instrument_key"]
    http = _FakeHttp(
        search={"TCS": {"status": "success", "data": [_TCS_NSE, _TCS_BSE]}},
        quotes={key: _quote_row(symbol="TCS", price=4100.0, key=key)},
    )
    adapter = UpstoxQuoteAdapter(access_token="tok", http_client=http)
    quote = adapter.get_quote(
        Instrument(
            symbol="TCS",
            asset_class=AssetClass.EQUITY,
            currency="INR",
            exchange="NSE",
        )
    )
    assert quote is not None
    assert quote.exchange == "NSE"
    assert float(quote.current_price.value) == pytest.approx(4100.0)


def test_token_not_in_public_dict() -> None:
    secret = "must-not-leak-u2"
    key = _INFY["instrument_key"]
    http = _FakeHttp(
        search={"INFY": {"status": "success", "data": [_INFY]}},
        quotes={key: _quote_row(symbol="INFY", price=10.0, key=key)},
    )
    client = UpstoxMarketQuoteClient(access_token=secret, http_client=http)
    blob = str(client.get_quote("INFY").to_public_dict())
    assert secret not in blob
    assert "Bearer" not in blob


def test_live_upstox_u2_quote_optional() -> None:
    from data_engine.upstox_connectivity import resolve_u0_upstox_analytics_token

    token = resolve_u0_upstox_analytics_token()
    if not token:
        pytest.skip("UPSTOX U2 LIVE TEST = NOT RUN; REASON = CREDENTIAL ABSENT")

    client = UpstoxMarketQuoteClient()
    for symbol in ("TCS", "INFY", "RELIANCE", "HDFCBANK", "SBIN", "TATAMOTORS"):
        result = client.get_quote(
            UpstoxMarketQuoteRequest(symbol=symbol, preferred_exchange="NSE")
        )
        assert token not in result.detail
        assert token not in str(result.to_public_dict())
        assert result.status in {"OK", "AMBIGUOUS", "NOT_FOUND", "UNAVAILABLE"}
        if result.status == "OK":
            assert result.quote is not None
            assert result.quote.current_price.available
            assert result.quote.currency == "INR"
            assert result.identity is not None
