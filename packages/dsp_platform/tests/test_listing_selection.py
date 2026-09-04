"""Stage 4P ? BSE-first / NSE-fallback listing policy (mocked candidates)."""

from __future__ import annotations

from dsp_platform.listing_selection import ListingCandidate, select_indian_listing

TCS_ISIN = "INE467B01029"
OTHER_ISIN = "INE999A01011"

def _c(exchange: str, isin: str = TCS_ISIN) -> ListingCandidate:
    return ListingCandidate(exchange=exchange, isin=isin)


def test_dual_listed_same_isin_selects_bse() -> None:
    result = select_indian_listing("TCS", None, (_c("NSE"), _c("BSE")))
    assert result.status == "SELECTED"
    assert result.exchange == "BSE"
    assert result.isin == TCS_ISIN


def test_bse_only_selects_bse() -> None:
    result = select_indian_listing("BSEONLY", None, (_c("BSE"),))
    assert result.status == "SELECTED"
    assert result.exchange == "BSE"


def test_nse_only_falls_back_to_nse() -> None:
    result = select_indian_listing("NSEONLY", None, (_c("NSE"),))
    assert result.status == "SELECTED"
    assert result.exchange == "NSE"


def test_neither_indian_venue_not_found() -> None:
    result = select_indian_listing("NONE", None, ())
    assert result.status == "NOT_FOUND"
    assert result.exchange is None


def test_explicit_nse_overrides_bse_default() -> None:
    result = select_indian_listing("TCS", "NSE", (_c("NSE"), _c("BSE")))
    assert result.status == "SELECTED"
    assert result.exchange == "NSE"


def test_explicit_bse_selects_bse() -> None:
    result = select_indian_listing("TCS", "BSE", (_c("NSE"), _c("BSE")))
    assert result.status == "SELECTED"
    assert result.exchange == "BSE"


def test_explicit_nse_without_nse_listing_not_found() -> None:
    result = select_indian_listing("TCS", "NSE", (_c("BSE"),))
    assert result.status == "NOT_FOUND"
    assert result.exchange is None


def test_explicit_bse_without_bse_listing_not_found() -> None:
    result = select_indian_listing("TCS", "BSE", (_c("NSE"),))
    assert result.status == "NOT_FOUND"
    assert result.exchange is None


def test_multiple_isins_ambiguous() -> None:
    result = select_indian_listing(
        "FOO", None, (_c("NSE", TCS_ISIN), _c("BSE", OTHER_ISIN))
    )
    assert result.status == "AMBIGUOUS"
    assert result.exchange is None


def test_no_candidates_not_found() -> None:
    result = select_indian_listing("ZZZZ", None, [])
    assert result.status == "NOT_FOUND"


def test_tcs_bse_first_when_same_isin_bse_exists() -> None:
    result = select_indian_listing("tcs", None, (_c("nse"), _c("bse")))
    assert result.status == "SELECTED"
    assert result.exchange == "BSE"
    assert result.symbol == "TCS"


def test_nasdaq_candidates_not_applicable() -> None:
    result = select_indian_listing(
        "AAPL", None, (ListingCandidate(exchange="NASDAQ", isin="US0378331005"),)
    )
    assert result.status == "NOT_APPLICABLE"
    assert result.exchange is None


def test_explicit_nasdaq_not_applicable_and_not_remapped() -> None:
    result = select_indian_listing(
        "AAPL",
        "NASDAQ",
        (ListingCandidate(exchange="NASDAQ", isin="US0378331005"),),
    )
    assert result.status == "NOT_APPLICABLE"
    assert result.exchange == "NASDAQ"


def test_explicit_exchange_does_not_fallback_to_other_venue() -> None:
    nse_only = select_indian_listing("TCS", "BSE", (_c("NSE"),))
    bse_only = select_indian_listing("TCS", "NSE", (_c("BSE"),))
    assert nse_only.status == "NOT_FOUND"
    assert bse_only.status == "NOT_FOUND"
