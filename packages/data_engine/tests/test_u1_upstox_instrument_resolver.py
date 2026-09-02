"""U1 — Upstox instrument resolver unit tests (mocked HTTP; no live secrets)."""

from __future__ import annotations

from typing import Any, Mapping

import pytest

from contracts.enums import AssetClass
from data_engine.exceptions import ProviderRequestError
from data_engine.upstox_instrument_resolver import (
    UPSTOX_INSTRUMENT_SEARCH_ENDPOINT,
    UpstoxInstrumentResolver,
    UpstoxResolveRequest,
    normalize_user_symbol,
)


def _eq_row(
    *,
    symbol: str,
    name: str,
    exchange: str,
    isin: str,
    instrument_key: str | None = None,
    instrument_type: str = "EQ",
) -> dict[str, Any]:
    seg = f"{exchange}_EQ"
    return {
        "segment": seg,
        "name": name,
        "exchange": exchange,
        "isin": isin,
        "instrument_type": instrument_type,
        "instrument_key": instrument_key or f"{seg}|{isin}",
        "trading_symbol": symbol,
        "short_name": symbol,
    }


# Representative fixtures — not live evidence.
_FIXTURES: dict[str, list[dict[str, Any]]] = {
    "TCS": [
        _eq_row(
            symbol="TCS",
            name="Tata Consultancy Services Limited",
            exchange="NSE",
            isin="INE467B01029",
        ),
        _eq_row(
            symbol="TCS",
            name="Tata Consultancy Services Limited",
            exchange="BSE",
            isin="INE467B01029",
        ),
    ],
    "INFY": [
        _eq_row(
            symbol="INFY",
            name="Infosys Limited",
            exchange="NSE",
            isin="INE009A01021",
        ),
    ],
    "RELIANCE": [
        _eq_row(
            symbol="RELIANCE",
            name="Reliance Industries Limited",
            exchange="NSE",
            isin="INE002A01018",
        ),
    ],
    "HDFCBANK": [
        _eq_row(
            symbol="HDFCBANK",
            name="HDFC Bank Limited",
            exchange="NSE",
            isin="INE040A01034",
        ),
    ],
    "SBIN": [
        _eq_row(
            symbol="SBIN",
            name="State Bank of India",
            exchange="NSE",
            isin="INE062A01020",
        ),
    ],
    "TATAMOTORS": [
        _eq_row(
            symbol="TATAMOTORS",
            name="Tata Motors Limited",
            exchange="NSE",
            isin="INE155A01022",
        ),
    ],
}


class _FakeSearchHttp:
    def __init__(self, routes: Mapping[str, Any] | None = None, *, error: Exception | None = None) -> None:
        self._routes = dict(routes or {})
        self._error = error
        self.calls: list[dict[str, Any]] = []

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        self.calls.append(
            {"url": url, "params": dict(params or {}), "headers": dict(headers or {})}
        )
        if self._error is not None:
            raise self._error
        assert UPSTOX_INSTRUMENT_SEARCH_ENDPOINT in url
        assert headers and "Authorization" in headers
        assert str(headers["Authorization"]).startswith("Bearer ")
        q = str((params or {}).get("query") or "").upper()
        if q in self._routes:
            return self._routes[q]
        return {"status": "success", "data": []}


def _resolver_for(symbol: str, rows: list[dict[str, Any]] | None = None) -> UpstoxInstrumentResolver:
    data = rows if rows is not None else _FIXTURES.get(symbol, [])
    http = _FakeSearchHttp({symbol: {"status": "success", "data": data}})
    return UpstoxInstrumentResolver(access_token="u1-test-token", http_client=http)


def test_normalize_user_symbol_strips_harmless_suffix_not_authoritative() -> None:
    assert normalize_user_symbol(" tcs ") == "TCS"
    assert normalize_user_symbol("TCS.NS") == "TCS"
    assert normalize_user_symbol("reliance.bo") == "RELIANCE"
    # Does not invent a suffix.
    assert normalize_user_symbol("INFY") == "INFY"


@pytest.mark.parametrize(
    "symbol,expected_isin",
    [
        ("INFY", "INE009A01021"),
        ("RELIANCE", "INE002A01018"),
        ("HDFCBANK", "INE040A01034"),
        ("SBIN", "INE062A01020"),
        ("TATAMOTORS", "INE155A01022"),
    ],
)
def test_resolve_unique_equity(symbol: str, expected_isin: str) -> None:
    result = _resolver_for(symbol).resolve(symbol)
    assert result.status == "RESOLVED"
    assert result.identity is not None
    assert result.identity.trading_symbol == symbol
    assert result.identity.isin == expected_isin
    assert result.identity.exchange == "NSE"
    assert result.identity.provider == "upstox"
    assert result.identity.provider_instrument_id.startswith("NSE_EQ|")
    assert result.instrument is not None
    assert result.instrument.symbol == symbol
    assert result.instrument.isin == expected_isin
    assert result.instrument.currency == "INR"
    assert result.instrument.asset_class is AssetClass.EQUITY
    assert result.instrument.country == "IN"


def test_tcs_nse_and_bse_is_ambiguous_not_silent_pick() -> None:
    result = _resolver_for("TCS").resolve("TCS")
    assert result.status == "AMBIGUOUS"
    assert result.instrument is None
    assert len(result.candidates) == 2
    exchanges = {c.exchange for c in result.candidates}
    assert exchanges == {"NSE", "BSE"}
    assert all(c.isin == "INE467B01029" for c in result.candidates)


def test_tcs_preferred_exchange_resolves_uniquely() -> None:
    result = _resolver_for("TCS").resolve(
        UpstoxResolveRequest(symbol="TCS", preferred_exchange="NSE")
    )
    assert result.status == "RESOLVED"
    assert result.identity is not None
    assert result.identity.exchange == "NSE"
    assert result.identity.isin == "INE467B01029"


def test_preferred_nse_search_matches_known_good_query_contract() -> None:
    """TCS/NSE must hit Upstox as query=TCS&exchanges=NSE — no extra keys."""
    http = _FakeSearchHttp(
        {"TCS": {"status": "success", "data": _FIXTURES["TCS"]}}
    )
    resolver = UpstoxInstrumentResolver(access_token="tok", http_client=http)
    result = resolver.resolve(
        UpstoxResolveRequest(symbol="TCS", preferred_exchange="NSE")
    )
    assert result.status == "RESOLVED"
    assert len(http.calls) == 1
    assert http.calls[0]["params"] == {"query": "TCS", "exchanges": "NSE"}
    assert "Authorization" in http.calls[0]["headers"]
    assert http.calls[0]["headers"]["Accept"] == "application/json"


def test_unqualified_search_does_not_send_undocumented_paging_keys() -> None:
    http = _FakeSearchHttp(
        {"TCS": {"status": "success", "data": _FIXTURES["TCS"]}}
    )
    resolver = UpstoxInstrumentResolver(access_token="tok", http_client=http)
    result = resolver.resolve("TCS")
    assert result.status == "AMBIGUOUS"
    params = http.calls[0]["params"]
    assert params == {"query": "TCS", "exchanges": "NSE,BSE"}
    assert "segments" not in params
    assert "page_number" not in params
    assert "records" not in params


def test_unknown_symbol_not_found() -> None:
    http = _FakeSearchHttp({"ZZZZZZ": {"status": "success", "data": []}})
    resolver = UpstoxInstrumentResolver(access_token="tok", http_client=http)
    result = resolver.resolve("ZZZZZZ")
    assert result.status == "NOT_FOUND"
    assert result.instrument is None


def test_missing_isin_skipped() -> None:
    rows = [
        {
            "segment": "NSE_EQ",
            "name": "Broken Co",
            "exchange": "NSE",
            "isin": "",
            "instrument_type": "EQ",
            "instrument_key": "NSE_EQ|MISSING",
            "trading_symbol": "BROKEN",
        }
    ]
    result = _resolver_for("BROKEN", rows).resolve("BROKEN")
    assert result.status == "NOT_FOUND"


def test_missing_instrument_key_skipped() -> None:
    rows = [
        {
            "segment": "NSE_EQ",
            "name": "No Key Co",
            "exchange": "NSE",
            "isin": "INE000A01000",
            "instrument_type": "EQ",
            "instrument_key": "",
            "trading_symbol": "NOKEY",
        }
    ]
    result = _resolver_for("NOKEY", rows).resolve("NOKEY")
    assert result.status == "NOT_FOUND"


def test_wrong_exchange_segment_mismatch_skipped() -> None:
    rows = [
        {
            "segment": "NSE_EQ",
            "name": "Bad Label",
            "exchange": "BSE",  # mismatch with NSE_EQ segment
            "isin": "INE000A01001",
            "instrument_type": "EQ",
            "instrument_key": "NSE_EQ|INE000A01001",
            "trading_symbol": "BADX",
        }
    ]
    result = _resolver_for("BADX", rows).resolve("BADX")
    assert result.status == "NOT_FOUND"


def test_forged_client_isin_rejected() -> None:
    result = _resolver_for("INFY").resolve(
        UpstoxResolveRequest(symbol="INFY", client_isin="INE009A01021")
    )
    assert result.status == "REJECTED"
    assert result.instrument is None


def test_forged_client_instrument_key_rejected() -> None:
    result = _resolver_for("INFY").resolve(
        UpstoxResolveRequest(
            symbol="INFY", client_instrument_key="NSE_EQ|INE009A01021"
        )
    )
    assert result.status == "REJECTED"


def test_forged_client_provider_rejected() -> None:
    result = _resolver_for("INFY").resolve(
        UpstoxResolveRequest(symbol="INFY", client_provider="upstox")
    )
    assert result.status == "REJECTED"


def test_missing_credential_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DSP_UPSTOX_ANALYTICS_TOKEN", raising=False)
    monkeypatch.delenv("DSP_UPSTOX_ACCESS_TOKEN", raising=False)
    resolver = UpstoxInstrumentResolver(access_token="")
    result = resolver.resolve("TCS")
    assert result.status == "UNAVAILABLE"
    assert "absent" in result.detail.lower() or "unavailable" in result.detail.lower()


def test_production_missing_credential_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    resolver = UpstoxInstrumentResolver(access_token="")
    result = resolver.resolve("TCS")
    assert result.status == "UNAVAILABLE"
    assert "fail-closed" in result.detail.lower()
    assert "fixture" in result.detail.lower()


def test_provider_http_error_unavailable_no_token_leak() -> None:
    secret = "secret-u1-token"
    http = _FakeSearchHttp(
        error=ProviderRequestError(
            "HTTP 401 authentication failed for "
            "'https://api.upstox.com/v2/instruments/search'"
        )
    )
    resolver = UpstoxInstrumentResolver(access_token=secret, http_client=http)
    result = resolver.resolve("INFY")
    assert result.status == "UNAVAILABLE"
    assert result.http_status == 401
    assert secret not in result.detail


def test_token_not_in_public_dict() -> None:
    secret = "must-not-appear"
    http = _FakeSearchHttp(
        {"INFY": {"status": "success", "data": _FIXTURES["INFY"]}}
    )
    resolver = UpstoxInstrumentResolver(access_token=secret, http_client=http)
    payload = resolver.resolve("INFY").to_public_dict()
    blob = str(payload)
    assert secret not in blob
    assert "Bearer" not in blob


def test_live_upstox_u1_resolution_optional() -> None:
    """Live resolve only when DSP_UPSTOX_ANALYTICS_TOKEN is present."""
    from data_engine.upstox_connectivity import resolve_u0_upstox_analytics_token

    token = resolve_u0_upstox_analytics_token()
    if not token:
        pytest.skip("UPSTOX U1 LIVE TEST = NOT RUN; REASON = CREDENTIAL ABSENT")

    resolver = UpstoxInstrumentResolver()
    symbols = ("TCS", "INFY", "RELIANCE", "HDFCBANK", "SBIN", "TATAMOTORS")
    for symbol in symbols:
        result = resolver.resolve(
            UpstoxResolveRequest(symbol=symbol, preferred_exchange="NSE")
        )
        assert token not in result.detail
        assert token not in str(result.to_public_dict())
        assert result.status in {"RESOLVED", "AMBIGUOUS", "NOT_FOUND", "UNAVAILABLE"}
        if result.status == "RESOLVED":
            assert result.identity is not None
            assert result.identity.isin
            assert result.identity.provider_instrument_id
            assert result.identity.exchange == "NSE"
