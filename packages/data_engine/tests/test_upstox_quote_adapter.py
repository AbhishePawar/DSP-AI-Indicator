import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.exceptions import ProviderRequestError
from data_engine.market_quote.upstox_adapter import UpstoxQuoteAdapter


def test_unconfigured_upstox_adapter() -> None:
    adapter = UpstoxQuoteAdapter(access_token=None, api_key=None)
    assert not adapter.is_configured()
    h = adapter.health()
    assert not h.healthy
    assert not h.authenticated
    assert "not configured" in h.detail

    inst = Instrument(
        symbol="TATAMOTORS",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )
    assert adapter.get_quote(inst) is None


def test_instrument_key_formatting() -> None:
    adapter = UpstoxQuoteAdapter(access_token="test_token")
    eq_nse = Instrument(
        symbol="TATAMOTORS",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )
    assert adapter.format_instrument_key(eq_nse) == "NSE_EQ|TATAMOTORS"

    eq_bse = Instrument(
        symbol="500570",
        exchange="BSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )
    assert adapter.format_instrument_key(eq_bse) == "BSE_EQ|500570"

    comm = Instrument(
        symbol="GOLD",
        exchange="MCX",
        asset_class=AssetClass.COMMODITY,
        currency="INR",
    )
    assert adapter.format_instrument_key(comm) == "MCX_COMM|GOLD"


def test_upstox_quote_mock_response() -> None:
    adapter = UpstoxQuoteAdapter(
        access_token="mock_access_token",
        base_url="https://api.upstox.com/v2",
    )
    assert adapter.is_configured()
    assert adapter.health().healthy

    inst = Instrument(
        symbol="TATAMOTORS",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )

    mock_payload = {
        "status": "success",
        "data": {
            "NSE_EQ:TATAMOTORS": {
                "ohlc": {
                    "open": 980.0,
                    "high": 995.0,
                    "low": 975.0,
                    "close": 985.0,
                },
                "last_price": 992.5,
                "volume": 2500000,
                "net_change": 7.5,
                "timestamp": "2026-04-18T10:30:00.000Z",
            }
        },
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False

    with patch("urllib.request.urlopen", return_value=mock_resp):
        quote = adapter.get_quote(inst)

    assert quote is not None
    assert quote.symbol == "TATAMOTORS"
    assert quote.current_price.value == 992.5
    assert quote.open.value == 980.0
    assert quote.high.value == 995.0
    assert quote.low.value == 975.0
    assert quote.previous_close.value == 985.0
    assert quote.volume.value == 2500000
    assert quote.provenance.provider_id == "upstox"
    assert quote.provenance.auth_mode == "oauth_bearer"


def test_upstox_quote_404_returns_none() -> None:
    adapter = UpstoxQuoteAdapter(access_token="mock_token")
    inst = Instrument(
        symbol="UNKNOWN",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )
    http_error = urllib.error.HTTPError(
        url="https://api.upstox.com/v2/market-quote/quotes",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=io.BytesIO(b""),
    )
    with patch("urllib.request.urlopen", side_effect=http_error):
        res = adapter.get_quote(inst)
    assert res is None


def test_upstox_quote_401_raises_provider_error() -> None:
    adapter = UpstoxQuoteAdapter(access_token="invalid_token")
    inst = Instrument(
        symbol="TATAMOTORS",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )
    http_error = urllib.error.HTTPError(
        url="https://api.upstox.com/v2/market-quote/quotes",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=io.BytesIO(b""),
    )
    with patch("urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(ProviderRequestError) as exc_info:
            adapter.get_quote(inst)
        assert "authentication failed" in str(exc_info.value)
