"""Comprehensive tests for Upstox V3 Historical Candle Adapter."""

from __future__ import annotations

import io
import json
import urllib.error
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.exceptions import InvalidProviderDataError, ProviderRequestError
from data_engine.historical_series.adapters import (
    build_default_historical_adapter_from_env,
)
from data_engine.historical_series.service import HistoricalSeriesQuery
from data_engine.historical_series.upstox_adapter import (
    UpstoxCandle,
    UpstoxHistoricalAdapter,
)
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
    ]
    return UpstoxInstrumentResolver(records=records)


def test_unconfigured_historical_adapter() -> None:
    adapter = UpstoxHistoricalAdapter(access_token=None)
    assert not adapter.is_configured()
    h = adapter.health()
    assert not h.healthy
    assert not h.authenticated
    assert "UPSTOX_ACCESS_TOKEN not set" in h.detail

    query = HistoricalSeriesQuery(
        instrument=Instrument(
            symbol="NHPC",
            exchange="NSE",
            asset_class=AssetClass.EQUITY,
            currency="INR",
        ),
        series_kind="ohlcv",
    )
    assert adapter.get_series(query) is None


def test_historical_secret_leakage_prevention() -> None:
    secret = "HIST_UPSTOX_SECRET_TOKEN_999"
    adapter = UpstoxHistoricalAdapter(access_token=secret)
    assert secret not in repr(adapter)
    assert secret not in str(adapter)
    assert secret not in (adapter.health().detail or "")


def test_v3_historical_candle_endpoint_url_and_headers(test_resolver: UpstoxInstrumentResolver) -> None:
    adapter = UpstoxHistoricalAdapter(
        access_token="valid_hist_token",
        resolver=test_resolver,
    )

    captured_req: list[urllib.request.Request] = []

    def mock_urlopen(req: urllib.request.Request, timeout: float = 12.0):
        captured_req.append(req)
        resp = MagicMock()
        payload = {
            "status": "success",
            "data": {
                "candles": [
                    ["2026-04-17T09:15:00+05:30", 94.0, 96.0, 93.5, 95.2, 100000, 5000],
                    ["2026-04-18T09:15:00+05:30", 95.5, 97.0, 95.0, 96.8, 120000, 6000],
                ]
            },
        }
        resp.read.return_value = json.dumps(payload).encode("utf-8")
        resp.status = 200
        resp.__enter__.return_value = resp
        resp.__exit__.return_value = False
        return resp

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        candles = adapter.get_candles(
            instrument_key="NSE_EQ|INE848E01016",
            unit="days",
            interval=1,
            to_date="2026-04-18",
            from_date="2026-04-01",
        )

    assert len(captured_req) == 1
    req = captured_req[0]
    expected_path = "/v3/historical-candle/NSE_EQ%7CINE848E01016/days/1/2026-04-18/2026-04-01"
    assert expected_path in req.full_url
    assert req.headers["Authorization"] == "Bearer valid_hist_token"
    assert req.headers["Accept"] == "application/json"
    assert len(candles) == 2


def test_v3_historical_candle_parsing_and_sorting(test_resolver: UpstoxInstrumentResolver) -> None:
    adapter = UpstoxHistoricalAdapter(access_token="tok", resolver=test_resolver)

    # API returns newest first (reverse chronological)
    payload = {
        "status": "success",
        "data": {
            "candles": [
                ["2026-04-18T09:15:00+05:30", 95.0, 98.0, 94.0, 97.5, 50000, 1000.0],
                ["2026-04-17T09:15:00+05:30", 92.0, 95.5, 91.5, 94.8, 45000, 850.0],
            ]
        },
    }

    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.status = 200
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False

    with patch("urllib.request.urlopen", return_value=resp):
        candles = adapter.get_candles(
            instrument_key="NSE_EQ|INE848E01016",
            unit="days",
            interval=1,
            to_date="2026-04-18",
            from_date="2026-04-17",
        )

    # Must be sorted in ascending chronological order
    assert len(candles) == 2
    assert candles[0].timestamp.startswith("2026-04-17")
    assert candles[0].open == 92.0
    assert candles[0].close == 94.8
    assert candles[0].volume == 45000
    assert candles[0].open_interest == 850.0

    assert candles[1].timestamp.startswith("2026-04-18")
    assert candles[1].open == 95.0
    assert candles[1].close == 97.5
    assert candles[1].volume == 50000
    assert candles[1].open_interest == 1000.0


def test_v3_historical_candle_units_validation() -> None:
    adapter = UpstoxHistoricalAdapter(access_token="tok")

    # Documented units are valid
    for u in ("minutes", "hours", "days", "weeks", "months"):
        unit, interval, to_s, from_s = adapter.validate_request_parameters(
            unit=u,
            interval=1,
            to_date="2026-04-10",
            from_date="2026-04-01",
        )
        assert unit == u

    # Invalid unit raises
    with pytest.raises(ProviderRequestError) as exc:
        adapter.validate_request_parameters(
            unit="seconds",
            interval=1,
            to_date="2026-04-10",
            from_date="2026-04-01",
        )
    assert "Unsupported candle unit" in str(exc.value)


def test_v3_historical_candle_date_ordering_validation() -> None:
    adapter = UpstoxHistoricalAdapter(access_token="tok")
    # from_date is after to_date
    with pytest.raises(ProviderRequestError) as exc:
        adapter.validate_request_parameters(
            unit="days",
            interval=1,
            to_date="2026-04-01",
            from_date="2026-04-10",
        )
    assert "Date ordering violation" in str(exc.value)


def test_v3_historical_candle_window_limit_validation() -> None:
    adapter = UpstoxHistoricalAdapter(access_token="tok")
    # minutes max window is 100 days; test with 150 days
    with pytest.raises(ProviderRequestError) as exc:
        adapter.validate_request_parameters(
            unit="minutes",
            interval=1,
            to_date="2026-06-01",
            from_date="2026-01-01",
        )
    assert "exceeds maximum retrieval window" in str(exc.value)


def test_v3_historical_candle_401_authentication_failure(test_resolver: UpstoxInstrumentResolver) -> None:
    adapter = UpstoxHistoricalAdapter(access_token="bad_tok", resolver=test_resolver)
    http_error = urllib.error.HTTPError(
        url="https://api.upstox.com/v3/historical-candle/...",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=io.BytesIO(b'{"status":"error"}'),
    )
    with patch("urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(ProviderRequestError) as exc:
            adapter.get_candles(
                instrument_key="NSE_EQ|INE848E01016",
                unit="days",
                interval=1,
                to_date="2026-04-10",
                from_date="2026-04-01",
            )
        assert "authentication failed" in str(exc.value)


def test_v3_historical_candle_404_empty_return(test_resolver: UpstoxInstrumentResolver) -> None:
    adapter = UpstoxHistoricalAdapter(access_token="tok", resolver=test_resolver)
    http_error = urllib.error.HTTPError(
        url="https://api.upstox.com/v3/historical-candle/...",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=io.BytesIO(b""),
    )
    with patch("urllib.request.urlopen", side_effect=http_error):
        res = adapter.get_candles(
            instrument_key="NSE_EQ|INE848E01016",
            unit="days",
            interval=1,
            to_date="2026-04-10",
            from_date="2026-04-01",
        )
    assert res == []


def test_v3_historical_series_bundle_construction(test_resolver: UpstoxInstrumentResolver) -> None:
    adapter = UpstoxHistoricalAdapter(
        access_token="valid_hist_token",
        resolver=test_resolver,
    )

    query = HistoricalSeriesQuery(
        instrument=Instrument(
            symbol="NHPC",
            exchange="NSE",
            asset_class=AssetClass.EQUITY,
            currency="INR",
        ),
        series_kind="ohlcv",
        frequency="daily",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 18),
    )

    payload = {
        "status": "success",
        "data": {
            "candles": [
                ["2026-04-18T09:15:00+05:30", 95.0, 98.0, 94.0, 97.5, 50000, 1000.0],
                ["2026-04-17T09:15:00+05:30", 92.0, 95.5, 91.5, 94.8, 45000, 850.0],
            ]
        },
    }

    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.status = 200
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False

    with patch("urllib.request.urlopen", return_value=resp):
        bundle = adapter.get_series(query)

    assert bundle is not None
    assert bundle.series_kind == "ohlcv"
    assert bundle.frequency == "daily"
    assert len(bundle.bars) == 2
    # Verify bars are ascending
    assert bundle.bars[0].bar_date == date(2026, 4, 17)
    assert bundle.bars[1].bar_date == date(2026, 4, 18)
    assert bundle.provenance.provider_id == "upstox"
    assert bundle.provenance.auth_mode == "oauth_bearer"


def test_factory_historical_selection_with_upstox_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "mock_server_token_456")
    monkeypatch.delenv("DSP_HISTORICAL_SERIES_API_KEY", raising=False)
    monkeypatch.delenv("DSP_HISTORICAL_SERIES_BASE_URL", raising=False)
    monkeypatch.delenv("DSP_HISTORICAL_SERIES_MEMORY", raising=False)

    adapter = build_default_historical_adapter_from_env()
    assert isinstance(adapter, UpstoxHistoricalAdapter)
    assert adapter.is_configured()
    assert adapter.provider_id == "upstox"
