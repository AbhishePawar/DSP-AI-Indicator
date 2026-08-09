"""U3 — Upstox authenticated historical candles via U1 identity (mocked HTTP)."""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping
from urllib.parse import unquote

import pytest

from data_engine.exceptions import ProviderRequestError
from data_engine.upstox_historical_candles import (
    UPSTOX_HISTORICAL_CANDLE_PATH,
    UpstoxHistoricalCandleClient,
    UpstoxHistoricalCandleRequest,
    _chunk_date_windows,
    _historical_url,
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


def _candle(
    ts: str,
    o: float,
    h: float,
    l: float,
    c: float,
    vol: int = 1000,
    oi: int = 0,
) -> list[Any]:
    return [ts, o, h, l, c, vol, oi]


_INFY = _eq(symbol="INFY", name="Infosys Limited", exchange="NSE", isin="INE009A01021")
_TCS_NSE = _eq(symbol="TCS", name="Tata Consultancy Services Limited", exchange="NSE", isin="INE467B01029")
_TCS_BSE = _eq(symbol="TCS", name="Tata Consultancy Services Limited", exchange="BSE", isin="INE467B01029")


class _FakeHttp:
    def __init__(
        self,
        *,
        search: Mapping[str, Any],
        history: Mapping[str, Any] | None = None,
        error_on: str | None = None,
        error: Exception | None = None,
    ) -> None:
        self.search = dict(search)
        self.history = dict(history or {})
        self.error_on = error_on
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def get_json(self, url: str, *, params=None, headers=None):
        self.calls.append({"url": url, "params": dict(params or {}), "headers": dict(headers or {})})
        assert headers and str(headers.get("Authorization", "")).startswith("Bearer ")
        if self.error is not None and (self.error_on is None or self.error_on in url):
            raise self.error
        if "instruments/search" in url:
            q = str((params or {}).get("query") or "").upper()
            return self.search.get(q, {"status": "success", "data": []})
        if UPSTOX_HISTORICAL_CANDLE_PATH in url:
            # Match by decoded instrument key substring
            for key, payload in self.history.items():
                if key.replace("|", "%7C") in url or key in unquote(url):
                    return payload
            return {"status": "success", "data": {"candles": []}}
        raise AssertionError(url)


def _history_payload(candles: list[list[Any]]) -> dict[str, Any]:
    return {"status": "success", "data": {"candles": candles}}


def _client_for(
    *,
    search_rows: list[dict[str, Any]],
    symbol: str,
    candles: list[list[Any]] | None = None,
    history_payload: dict[str, Any] | None = None,
    error_on: str | None = None,
    error: Exception | None = None,
    token: str = "u3-test-token",
) -> UpstoxHistoricalCandleClient:
    key = search_rows[0]["instrument_key"] if len(search_rows) == 1 else ""
    history: dict[str, Any] = {}
    if len(search_rows) == 1:
        history[key] = history_payload or _history_payload(
            candles
            or [
                _candle("2024-01-02T00:00:00+05:30", 10, 12, 9, 11, 100),
                _candle("2024-01-03T00:00:00+05:30", 11, 13, 10, 12, 200),
            ]
        )
    http = _FakeHttp(
        search={symbol: {"status": "success", "data": search_rows}},
        history=history,
        error_on=error_on,
        error=error,
    )
    return UpstoxHistoricalCandleClient(access_token=token, http_client=http)


_FROM = date(2024, 1, 1)
_TO = date(2024, 1, 10)


def test_tcs_daily_history_via_u1_key() -> None:
    client = _client_for(search_rows=[_TCS_NSE], symbol="TCS")
    result = client.get_history(
        UpstoxHistoricalCandleRequest(
            symbol="TCS",
            from_date=_FROM,
            to_date=_TO,
            interval="daily",
            preferred_exchange="NSE",
        )
    )
    assert result.status == "OK"
    assert result.identity is not None
    assert result.identity.provider_instrument_id == "NSE_EQ|INE467B01029"
    assert result.series is not None
    assert result.series.currency == "INR"
    assert result.series.identity.exchange == "NSE"
    assert result.candle_count == 2
    # U1 instrument_key used in historical URL
    hist_calls = [c for c in client.http_client.calls if UPSTOX_HISTORICAL_CANDLE_PATH in c["url"]]  # type: ignore[union-attr]
    assert hist_calls
    assert "NSE_EQ%7CINE467B01029" in hist_calls[0]["url"]
    assert "/day/" in hist_calls[0]["url"]


def test_infy_daily_history_normalization() -> None:
    client = _client_for(search_rows=[_INFY], symbol="INFY")
    result = client.get_history(
        UpstoxHistoricalCandleRequest(symbol="INFY", from_date=_FROM, to_date=_TO)
    )
    assert result.status == "OK"
    assert result.series is not None
    bars = result.series.bars
    assert bars[0].bar_date == date(2024, 1, 2)
    assert bars[1].bar_date == date(2024, 1, 3)
    assert float(bars[0].open.value) == 10
    assert float(bars[0].high.value) == 12
    assert float(bars[0].low.value) == 9
    assert float(bars[0].close.value) == 11
    assert float(bars[0].volume.value) == 100
    assert result.series.provenance.provider_id == "upstox_historical_candles"
    assert result.series.frequency == "daily"


def test_ambiguous_identity_prevents_history_request() -> None:
    client = _client_for(search_rows=[_TCS_NSE, _TCS_BSE], symbol="TCS")
    result = client.get_history(
        UpstoxHistoricalCandleRequest(symbol="TCS", from_date=_FROM, to_date=_TO)
    )
    assert result.status == "AMBIGUOUS"
    assert result.series is None
    hist_calls = [c for c in client.http_client.calls if UPSTOX_HISTORICAL_CANDLE_PATH in c["url"]]  # type: ignore[union-attr]
    assert hist_calls == []


def test_unresolved_identity_prevents_history_request() -> None:
    client = _client_for(search_rows=[], symbol="ZZZZ")
    result = client.get_history(
        UpstoxHistoricalCandleRequest(symbol="ZZZZ", from_date=_FROM, to_date=_TO)
    )
    assert result.status == "NOT_FOUND"
    assert result.series is None


def test_client_instrument_key_forgery_rejected() -> None:
    client = _client_for(search_rows=[_INFY], symbol="INFY")
    result = client.get_history(
        UpstoxHistoricalCandleRequest(
            symbol="INFY",
            from_date=_FROM,
            to_date=_TO,
            client_instrument_key="NSE_EQ|FORGED",
        )
    )
    assert result.status == "REJECTED"
    assert "not authoritative" in result.detail


def test_client_candles_rejected() -> None:
    client = _client_for(search_rows=[_INFY], symbol="INFY")
    result = client.get_history(
        UpstoxHistoricalCandleRequest(
            symbol="INFY",
            from_date=_FROM,
            to_date=_TO,
            client_candles=[[_candle("2024-01-02T00:00:00+05:30", 1, 2, 0.5, 1.5)]],
        )
    )
    assert result.status == "REJECTED"


def test_date_range_validation() -> None:
    client = _client_for(search_rows=[_INFY], symbol="INFY")
    result = client.get_history(
        UpstoxHistoricalCandleRequest(
            symbol="INFY",
            from_date=date(2024, 2, 1),
            to_date=date(2024, 1, 1),
        )
    )
    assert result.status == "REJECTED"
    assert "from_date after to_date" in result.detail


def test_invalid_interval_rejected() -> None:
    client = _client_for(search_rows=[_INFY], symbol="INFY")
    result = client.get_history(
        UpstoxHistoricalCandleRequest(
            symbol="INFY",
            from_date=_FROM,
            to_date=_TO,
            interval="1minute",
        )
    )
    assert result.status == "REJECTED"
    assert "unsupported interval" in result.detail


def test_chronological_ordering() -> None:
    # Provider returns newest-first (as Upstox sample docs show)
    candles = [
        _candle("2024-01-05T00:00:00+05:30", 14, 15, 13, 14.5),
        _candle("2024-01-02T00:00:00+05:30", 10, 11, 9, 10.5),
        _candle("2024-01-04T00:00:00+05:30", 12, 13, 11, 12.5),
    ]
    client = _client_for(search_rows=[_INFY], symbol="INFY", candles=candles)
    result = client.get_history(
        UpstoxHistoricalCandleRequest(symbol="INFY", from_date=_FROM, to_date=_TO)
    )
    assert result.status == "OK"
    dates = [b.bar_date for b in result.series.bars]  # type: ignore[union-attr]
    assert dates == sorted(dates)
    assert dates == [date(2024, 1, 2), date(2024, 1, 4), date(2024, 1, 5)]


def test_timestamp_normalization_ist() -> None:
    candles = [_candle("2024-01-02T15:30:00+05:30", 10, 11, 9, 10.5)]
    client = _client_for(search_rows=[_INFY], symbol="INFY", candles=candles)
    result = client.get_history(
        UpstoxHistoricalCandleRequest(symbol="INFY", from_date=_FROM, to_date=_TO)
    )
    assert result.series.bars[0].bar_date == date(2024, 1, 2)  # type: ignore[union-attr]


def test_empty_history() -> None:
    client = _client_for(
        search_rows=[_INFY],
        symbol="INFY",
        history_payload=_history_payload([]),
    )
    result = client.get_history(
        UpstoxHistoricalCandleRequest(symbol="INFY", from_date=_FROM, to_date=_TO)
    )
    assert result.status == "EMPTY"
    assert result.series is None
    assert result.candle_count == 0


def test_malformed_response() -> None:
    client = _client_for(
        search_rows=[_INFY],
        symbol="INFY",
        history_payload={"status": "success", "data": {"candles": "nope"}},
    )
    result = client.get_history(
        UpstoxHistoricalCandleRequest(symbol="INFY", from_date=_FROM, to_date=_TO)
    )
    assert result.status == "UNAVAILABLE"
    assert "malformed" in result.detail


def test_missing_ohlc_field_skips_candle() -> None:
    candles = [
        ["2024-01-02T00:00:00+05:30", 10, 12, 9, None, 100, 0],  # missing close
        _candle("2024-01-03T00:00:00+05:30", 11, 13, 10, 12, 200),
    ]
    client = _client_for(search_rows=[_INFY], symbol="INFY", candles=candles)
    result = client.get_history(
        UpstoxHistoricalCandleRequest(symbol="INFY", from_date=_FROM, to_date=_TO)
    )
    assert result.status == "OK"
    assert result.candle_count == 1
    assert result.series.bars[0].bar_date == date(2024, 1, 3)  # type: ignore[union-attr]


@pytest.mark.parametrize("code,fragment", [(401, "401"), (403, "403"), (404, "404"), (429, "429")])
def test_http_errors(code: int, fragment: str) -> None:
    client = _client_for(
        search_rows=[_INFY],
        symbol="INFY",
        error_on=UPSTOX_HISTORICAL_CANDLE_PATH,
        error=ProviderRequestError(
            f"HTTP {fragment} for 'https://api.upstox.com/v2/{UPSTOX_HISTORICAL_CANDLE_PATH}'"
        ),
    )
    result = client.get_history(
        UpstoxHistoricalCandleRequest(symbol="INFY", from_date=_FROM, to_date=_TO)
    )
    assert result.status == "UNAVAILABLE"
    assert fragment in result.detail
    assert result.http_status == code


def test_timeout_unavailable() -> None:
    client = _client_for(
        search_rows=[_INFY],
        symbol="INFY",
        error_on=UPSTOX_HISTORICAL_CANDLE_PATH,
        error=ProviderRequestError(
            "HTTP request to 'https://api.upstox.com/v2/historical-candle/...' failed: TimeoutError"
        ),
    )
    result = client.get_history(
        UpstoxHistoricalCandleRequest(symbol="INFY", from_date=_FROM, to_date=_TO)
    )
    assert result.status == "UNAVAILABLE"


def test_missing_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DSP_UPSTOX_ANALYTICS_TOKEN", raising=False)
    client = UpstoxHistoricalCandleClient(access_token="")
    result = client.get_history(
        UpstoxHistoricalCandleRequest(symbol="INFY", from_date=_FROM, to_date=_TO)
    )
    assert result.status == "UNAVAILABLE"
    assert "absent" in result.detail.lower()


def test_production_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.delenv("DSP_UPSTOX_ANALYTICS_TOKEN", raising=False)
    client = UpstoxHistoricalCandleClient(access_token="")
    result = client.get_history(
        UpstoxHistoricalCandleRequest(symbol="INFY", from_date=_FROM, to_date=_TO)
    )
    assert result.status == "UNAVAILABLE"
    assert "fail-closed" in result.detail.lower()


def test_token_not_in_public_dict() -> None:
    client = _client_for(search_rows=[_INFY], symbol="INFY", token="super-secret-u3-token")
    result = client.get_history(
        UpstoxHistoricalCandleRequest(symbol="INFY", from_date=_FROM, to_date=_TO)
    )
    blob = str(result.to_public_dict())
    assert "super-secret-u3-token" not in blob
    assert "Bearer" not in blob


def test_bounded_chunking_for_multi_year_daily() -> None:
    windows = _chunk_date_windows(
        date(2020, 1, 1),
        date(2023, 1, 1),
        interval="day",
        max_chunks=15,
    )
    assert len(windows) >= 2
    assert windows[0][0] == date(2020, 1, 1)
    assert windows[-1][1] == date(2023, 1, 1)
    # each window ≤ 365 days
    for start, end in windows:
        assert (end - start).days <= 364


def test_chunk_limit_fail_closed() -> None:
    windows = _chunk_date_windows(
        date(2000, 1, 1),
        date(2024, 1, 1),
        interval="day",
        max_chunks=2,
    )
    assert windows == []


def test_historical_url_encodes_instrument_key() -> None:
    url = _historical_url(
        "https://api.upstox.com/v2",
        instrument_key="NSE_EQ|INE009A01021",
        interval="day",
        to_date=date(2024, 1, 10),
        from_date=date(2024, 1, 1),
    )
    assert url == (
        "https://api.upstox.com/v2/historical-candle/"
        "NSE_EQ%7CINE009A01021/day/2024-01-10/2024-01-01"
    )


def test_live_upstox_u3_history_optional() -> None:
    from data_engine.upstox_connectivity import resolve_u0_upstox_analytics_token

    token = resolve_u0_upstox_analytics_token()
    if not token:
        pytest.skip("UPSTOX U3 LIVE TEST = NOT RUN; REASON = CREDENTIAL ABSENT")
    client = UpstoxHistoricalCandleClient(access_token=token)
    result = client.get_history(
        UpstoxHistoricalCandleRequest(
            symbol="TCS",
            from_date=date(2024, 1, 2),
            to_date=date(2024, 1, 15),
            interval="daily",
            preferred_exchange="NSE",
        )
    )
    assert result.status in {"OK", "EMPTY", "UNAVAILABLE"}
    pub = str(result.to_public_dict())
    assert token not in pub
