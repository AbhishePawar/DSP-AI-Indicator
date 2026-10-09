"""Comprehensive tests for Upstox V3 Market Quote Adapter."""

from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.exceptions import InvalidProviderDataError, ProviderRequestError
from data_engine.market_quote.adapters import build_default_quote_adapter_from_env
from data_engine.market_quote.upstox_adapter import UpstoxQuoteAdapter
from data_engine.upstox.instrument_resolver import (
    UpstoxInstrumentRecord,
    UpstoxInstrumentResolver,
)


@pytest.fixture
def test_resolver() -> UpstoxInstrumentResolver:
    records = [
        UpstoxInstrumentRecord(
            instrument_key="NSE_EQ|INE848E01016",
            symbol="NHPC",
            name="NHPC Limited",
            exchange="NSE",
            instrument_type="EQUITY",
            isin="INE848E01016",
        ),
        UpstoxInstrumentRecord(
            instrument_key="NSE_EQ|INE155A01022",
            symbol="TATAMOTORS",
            name="Tata Motors Limited",
            exchange="NSE",
            instrument_type="EQUITY",
            isin="INE155A01022",
        ),
        UpstoxInstrumentRecord(
            instrument_key="BSE_EQ|500570",
            symbol="TATAMOTORS",
            name="Tata Motors Limited",
            exchange="BSE",
            instrument_type="EQUITY",
            isin="INE155A01022",
        ),
    ]
    return UpstoxInstrumentResolver(records=records)


def test_unconfigured_upstox_adapter() -> None:
    adapter = UpstoxQuoteAdapter(access_token=None)
    assert not adapter.is_configured()
    h = adapter.health()
    assert not h.healthy
    assert not h.authenticated
    assert "UPSTOX_ACCESS_TOKEN not set" in h.detail

    inst = Instrument(
        symbol="TATAMOTORS",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )
    assert adapter.get_quote(inst) is None


def test_secret_leakage_prevention() -> None:
    secret_token = "SECRET_UPSTOX_ACCESS_TOKEN_XYZ_12345"
    adapter = UpstoxQuoteAdapter(access_token=secret_token)

    # Token must not appear in string repr
    rep = repr(adapter)
    assert secret_token not in rep
    s = str(adapter)
    assert secret_token not in s

    # Token must not leak in health check
    health_detail = adapter.health().detail or ""
    assert secret_token not in health_detail


def test_v3_quote_url_headers_and_params(test_resolver: UpstoxInstrumentResolver) -> None:
    adapter = UpstoxQuoteAdapter(
        access_token="valid_test_token",
        resolver=test_resolver,
    )

    inst = Instrument(
        symbol="NHPC",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )

    captured_req: list[urllib.request.Request] = []

    def mock_urlopen(req: urllib.request.Request, timeout: float = 10.0):
        captured_req.append(req)
        resp = MagicMock()
        payload = {
            "status": "success",
            "data": {
                "NSE_EQ:NHPC": {
                    "last_price": 95.5,
                    "volume": 1200000,
                    "timestamp": "2026-04-18T10:00:00+05:30",
                }
            },
        }
        resp.read.return_value = json.dumps(payload).encode("utf-8")
        resp.status = 200
        resp.__enter__.return_value = resp
        resp.__exit__.return_value = False
        return resp

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        quote = adapter.get_quote(inst)

    assert len(captured_req) == 1
    req = captured_req[0]

    # Verify official V3 endpoint
    assert req.full_url.startswith("https://api.upstox.com/v3/market-quote/quotes")
    # Verify query parameter format
    assert "instrument_key=NSE_EQ%7CINE848E01016" in req.full_url or "instrument_key=NSE_EQ|INE848E01016" in req.full_url
    # Verify authentication and headers
    assert req.headers["Authorization"] == "Bearer valid_test_token"
    assert req.headers["Accept"] == "application/json"
    assert quote is not None
    assert quote.symbol == "NHPC"
    assert quote.current_price.value == 95.5


def test_v3_quote_full_response_parsing(test_resolver: UpstoxInstrumentResolver) -> None:
    adapter = UpstoxQuoteAdapter(
        access_token="valid_test_token",
        resolver=test_resolver,
    )

    inst = Instrument(
        symbol="TATAMOTORS",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )

    # Documented Upstox V3 Market Quote response payload
    v3_payload = {
        "status": "success",
        "data": {
            "NSE_EQ:TATAMOTORS": {
                "ohlc": {
                    "open": 980.5,
                    "high": 995.0,
                    "low": 972.25,
                    "close": 988.0,
                    "volume": 2850000,
                    "ts": "2026-04-18T10:30:00+05:30",
                },
                "depth": {
                    "buy": [{"quantity": 100, "price": 987.5, "orders": 2}],
                    "sell": [{"quantity": 250, "price": 988.0, "orders": 5}],
                },
                "timestamp": "2026-04-18T10:30:01+05:30",
                "instrument_token": "NSE_EQ|INE155A01022",
                "symbol": "NSE_EQ:TATAMOTORS",
                "last_price": 988.0,
                "volume": 2850000,
                "average_price": 984.75,
                "oi": 15000.0,
                "net_change": 7.5,
                "total_buy_quantity": 45000.0,
                "total_sell_quantity": 62000.0,
                "lower_circuit_limit": 889.0,
                "upper_circuit_limit": 1086.0,
                "last_trade_time": "2026-04-18T10:30:00+05:30",
                "oi_day_high": 16000.0,
                "oi_day_low": 14000.0,
                "prev_close_price": 980.5,
                "year_high": 1065.0,
                "year_low": 650.0,
            }
        },
    }

    resp = MagicMock()
    resp.read.return_value = json.dumps(v3_payload).encode("utf-8")
    resp.status = 200
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False

    with patch("urllib.request.urlopen", return_value=resp):
        quote = adapter.get_quote(inst)

    assert quote is not None
    assert quote.symbol == "TATAMOTORS"
    assert quote.exchange == "NSE"
    assert quote.current_price.value == 988.0
    assert quote.open.value == 980.5
    assert quote.high.value == 995.0
    assert quote.low.value == 972.25
    assert float(quote.previous_close.value) == 980.5  # Taken from prev_close_price!
    assert quote.volume.value == 2850000
    assert quote.week_52_high.value == 1065.0
    assert quote.week_52_low.value == 650.0
    assert quote.provenance.provider_id == "upstox"
    assert quote.provenance.auth_mode == "oauth_bearer"

    # Verify metadata preserves optional V3 fields without losing types
    meta = quote.provenance.metadata
    assert meta["average_price"] == 984.75
    assert meta["net_change"] == 7.5
    assert meta["open_interest"] == 15000.0
    assert "depth" in meta
    assert meta["circuit_limits"]["lower"] == 889.0
    assert meta["circuit_limits"]["upper"] == 1086.0


def test_v3_quote_response_key_mapping(test_resolver: UpstoxInstrumentResolver) -> None:
    # Crucial test: Upstox request uses pipe (NSE_EQ|INE848E01016)
    # but response key uses colon (NSE_EQ:NHPC)
    adapter = UpstoxQuoteAdapter(
        access_token="valid_token",
        resolver=test_resolver,
    )
    inst = Instrument(
        symbol="NHPC",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )

    v3_payload = {
        "status": "success",
        "data": {
            "NSE_EQ:NHPC": {
                "last_price": 94.2,
                "prev_close_price": 93.0,
                "timestamp": "2026-04-18T10:00:00+05:30",
            }
        },
    }

    resp = MagicMock()
    resp.read.return_value = json.dumps(v3_payload).encode("utf-8")
    resp.status = 200
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False

    with patch("urllib.request.urlopen", return_value=resp):
        quote = adapter.get_quote(inst)

    assert quote is not None
    assert quote.symbol == "NHPC"
    assert float(quote.current_price.value) == 94.2
    assert float(quote.previous_close.value) == 93.0


def test_v3_quote_optional_fields_no_zero_substitution(test_resolver: UpstoxInstrumentResolver) -> None:
    adapter = UpstoxQuoteAdapter(
        access_token="valid_token",
        resolver=test_resolver,
    )
    inst = Instrument(
        symbol="NHPC",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )

    # Minimal payload with many optional fields missing
    v3_payload = {
        "status": "success",
        "data": {
            "NSE_EQ:NHPC": {
                "last_price": 95.0,
                "timestamp": "2026-04-18T10:00:00+05:30",
            }
        },
    }

    resp = MagicMock()
    resp.read.return_value = json.dumps(v3_payload).encode("utf-8")
    resp.status = 200
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False

    with patch("urllib.request.urlopen", return_value=resp):
        quote = adapter.get_quote(inst)

    assert quote is not None
    assert quote.current_price.value == 95.0
    # Missing open, high, low, previous_close must be unavailable / None, NOT 0.0
    assert not quote.open.available and quote.open.value is None
    assert not quote.high.available and quote.high.value is None
    assert not quote.low.available and quote.low.value is None
    assert not quote.previous_close.available and quote.previous_close.value is None
    assert not quote.volume.available and quote.volume.value is None
    assert not quote.week_52_high.available and quote.week_52_high.value is None
    assert not quote.week_52_low.available and quote.week_52_low.value is None


def test_v3_quote_401_authentication_error(test_resolver: UpstoxInstrumentResolver) -> None:
    adapter = UpstoxQuoteAdapter(access_token="bad_token", resolver=test_resolver)
    inst = Instrument(
        symbol="NHPC",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )
    http_error = urllib.error.HTTPError(
        url="https://api.upstox.com/v3/market-quote/quotes",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=io.BytesIO(b'{"status":"error","errors":[{"message":"Invalid token"}]}'),
    )
    with patch("urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(ProviderRequestError) as exc_info:
            adapter.get_quote(inst)
        assert "authentication failed" in str(exc_info.value)


def test_v3_quote_404_returns_none(test_resolver: UpstoxInstrumentResolver) -> None:
    adapter = UpstoxQuoteAdapter(access_token="valid_token", resolver=test_resolver)
    inst = Instrument(
        symbol="NHPC",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )
    http_error = urllib.error.HTTPError(
        url="https://api.upstox.com/v3/market-quote/quotes",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=io.BytesIO(b""),
    )
    with patch("urllib.request.urlopen", side_effect=http_error):
        res = adapter.get_quote(inst)
    assert res is None


def test_v3_quote_429_rate_limiting(test_resolver: UpstoxInstrumentResolver) -> None:
    adapter = UpstoxQuoteAdapter(
        access_token="valid_token",
        resolver=test_resolver,
        max_retries=1,
    )
    inst = Instrument(
        symbol="NHPC",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )
    http_error = urllib.error.HTTPError(
        url="https://api.upstox.com/v3/market-quote/quotes",
        code=429,
        msg="Too Many Requests",
        hdrs={},
        fp=io.BytesIO(b""),
    )
    with patch("urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(ProviderRequestError) as exc_info:
            adapter.get_quote(inst)
        assert "rate limited" in str(exc_info.value) or "HTTP 429" in str(exc_info.value)


def test_v3_quote_malformed_json(test_resolver: UpstoxInstrumentResolver) -> None:
    adapter = UpstoxQuoteAdapter(access_token="valid_token", resolver=test_resolver)
    inst = Instrument(
        symbol="NHPC",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )
    resp = MagicMock()
    resp.read.return_value = b"<!DOCTYPE html><html>Broken Gateway</html>"
    resp.status = 200
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False

    with patch("urllib.request.urlopen", return_value=resp):
        with pytest.raises(InvalidProviderDataError):
            adapter.get_quote(inst)


def test_v3_quote_non_success_status(test_resolver: UpstoxInstrumentResolver) -> None:
    adapter = UpstoxQuoteAdapter(access_token="valid_token", resolver=test_resolver)
    inst = Instrument(
        symbol="NHPC",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )
    resp = MagicMock()
    resp.read.return_value = json.dumps({"status": "error", "message": "Symbol not active"}).encode("utf-8")
    resp.status = 200
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False

    with patch("urllib.request.urlopen", return_value=resp):
        with pytest.raises(ProviderRequestError) as exc:
            adapter.get_quote(inst)
        assert "Symbol not active" in str(exc.value)


def test_v3_quote_unresolved_instrument_returns_none() -> None:
    empty_resolver = UpstoxInstrumentResolver(records=[])
    adapter = UpstoxQuoteAdapter(access_token="valid_token", resolver=empty_resolver)
    inst = Instrument(
        symbol="UNKNOWN_TICKER",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )
    assert adapter.get_quote(inst) is None


def test_factory_selection_with_upstox_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "mock_server_token_123")
    monkeypatch.delenv("DSP_MARKET_QUOTE_API_KEY", raising=False)
    monkeypatch.delenv("DSP_MARKET_QUOTE_BASE_URL", raising=False)
    monkeypatch.delenv("DSP_MARKET_QUOTE_MEMORY", raising=False)

    adapter = build_default_quote_adapter_from_env()
    assert isinstance(adapter, UpstoxQuoteAdapter)
    assert adapter.is_configured()
    assert adapter.provider_id == "upstox"
