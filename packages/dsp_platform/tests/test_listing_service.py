"""Listing orchestration: U1 is searched without preferred_exchange."""

from __future__ import annotations

from types import SimpleNamespace

from data_engine.upstox_instrument_resolver import UpstoxResolveRequest
from dsp_platform.listing_selection import ListingCandidate
from dsp_platform.listing_service import (
    reset_listing_resolver_for_tests,
    select_listing_for_symbol,
)

TCS_ISIN = "INE467B01029"


class _FakeResolver:
    def __init__(self, result: object) -> None:
        self.result = result
        self.requests: list[object] = []

    def resolve(self, request: object) -> object:
        self.requests.append(request)
        return self.result


def _tcs_ambiguous():
    nse = SimpleNamespace(
        exchange="NSE",
        isin=TCS_ISIN,
        trading_symbol="TCS",
        display_symbol="TCS",
    )
    bse = SimpleNamespace(
        exchange="BSE",
        isin=TCS_ISIN,
        trading_symbol="TCS",
        display_symbol="TCS",
    )
    return SimpleNamespace(status="AMBIGUOUS", detail="dual", candidates=(nse, bse))


def setup_function() -> None:
    reset_listing_resolver_for_tests(None)


def teardown_function() -> None:
    reset_listing_resolver_for_tests(None)


def test_tcs_search_without_preferred_exchange_then_bse_selected() -> None:
    fake = _FakeResolver(_tcs_ambiguous())
    reset_listing_resolver_for_tests(fake)
    result = select_listing_for_symbol("TCS")
    assert result.status == "SELECTED"
    assert result.exchange == "BSE"
    assert result.isin == TCS_ISIN
    assert len(fake.requests) == 1
    req = fake.requests[0]
    assert isinstance(req, UpstoxResolveRequest)
    assert req.symbol == "TCS"
    assert req.preferred_exchange is None


def test_explicit_nse_does_not_run_bse_first() -> None:
    fake = _FakeResolver(_tcs_ambiguous())
    reset_listing_resolver_for_tests(fake)
    result = select_listing_for_symbol("TCS", explicit_exchange="NSE")
    assert result.status == "SELECTED"
    assert result.exchange == "NSE"
    req = fake.requests[0]
    assert isinstance(req, UpstoxResolveRequest)
    assert req.preferred_exchange is None


def test_injected_candidates_skip_resolver() -> None:
    fake = _FakeResolver(_tcs_ambiguous())
    reset_listing_resolver_for_tests(fake)
    result = select_listing_for_symbol(
        "TCS",
        candidates=(
            ListingCandidate(exchange="NSE", isin=TCS_ISIN),
            ListingCandidate(exchange="BSE", isin=TCS_ISIN),
        ),
    )
    assert result.exchange == "BSE"
    assert fake.requests == []


def test_unavailable_search_is_unavailable_not_not_found() -> None:
    fake = _FakeResolver(
        SimpleNamespace(status="UNAVAILABLE", detail="no token", candidates=())
    )
    reset_listing_resolver_for_tests(fake)
    result = select_listing_for_symbol("TCS")
    assert result.status == "UNAVAILABLE"
    assert result.exchange is None
