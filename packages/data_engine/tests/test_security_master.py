"""Official Security Master search and resolve (SIMPLE-WEB-04).

Provider-neutral. Identity is ISIN + MIC. No Upstox / Yahoo / FMP.
"""

from __future__ import annotations

from data_engine.security_master.catalog import SecurityMasterCatalog
from data_engine.security_master.models import SecurityListing
from data_engine.security_master.service import (
    SecurityMasterService,
    is_vendor_shaped_identity,
    normalize_security_query,
)

_INFY_NSE = SecurityListing(
    ticker="INFY",
    company_name="Infosys Limited",
    isin="INE009A01021",
    exchange="NSE",
    mic="XNSE",
    security_type="equity",
    eligibility=True,
    series="EQ",
)
_INFY_BSE = SecurityListing(
    ticker="INFY",
    company_name="Infosys Limited",
    isin="INE009A01021",
    exchange="BSE",
    mic="XBOM",
    security_type="equity",
    eligibility=True,
    series="EQ",
)
_HDFC_NSE = SecurityListing(
    ticker="HDFCBANK",
    company_name="HDFC Bank Limited",
    isin="INE040A01034",
    exchange="NSE",
    mic="XNSE",
    security_type="equity",
    eligibility=True,
    series="EQ",
)
_HDFC_BSE = SecurityListing(
    ticker="HDFCBANK",
    company_name="HDFC Bank Limited",
    isin="INE040A01034",
    exchange="BSE",
    mic="XBOM",
    security_type="equity",
    eligibility=True,
    series="EQ",
)
_WIPRO_NSE = SecurityListing(
    ticker="WIPRO",
    company_name="Wipro Limited",
    isin="INE075A01022",
    exchange="NSE",
    mic="XNSE",
    security_type="equity",
    eligibility=True,
    series="EQ",
)
_WIPRO_BSE = SecurityListing(
    ticker="WIPRO",
    company_name="Wipro Limited",
    isin="INE075A01022",
    exchange="BSE",
    mic="XBOM",
    security_type="equity",
    eligibility=True,
    series="EQ",
)
_WARRANT = SecurityListing(
    ticker="FAKEWARR",
    company_name="Fixture Warrant",
    isin="IN9999W01001",
    exchange="NSE",
    mic="XNSE",
    security_type="warrant",
    eligibility=False,
    series="W",
)


def _service() -> SecurityMasterService:
    return SecurityMasterService(
        SecurityMasterCatalog.from_listings(
            (
                _INFY_NSE,
                _INFY_BSE,
                _HDFC_NSE,
                _HDFC_BSE,
                _WIPRO_NSE,
                _WIPRO_BSE,
                _WARRANT,
            )
        )
    )


def test_normalize_strips_yahoo_suffix_without_inventing_exchange() -> None:
    assert normalize_security_query("infy.ns") == "infy"
    assert normalize_security_query("  HDFC Bank  ") == "HDFC Bank"


def test_vendor_shaped_identity_detected() -> None:
    assert is_vendor_shaped_identity("NSE_EQ|INE009A01021") is True
    assert is_vendor_shaped_identity("INFY") is False


def test_infy_nse_search_and_resolve() -> None:
    service = _service()
    search = service.search("INFY", exchange="NSE")
    assert search.status == "MATCHES"
    assert len(search.results) == 1
    infy = search.results[0]
    assert infy.company_name == "Infosys Limited"
    assert infy.ticker == "INFY"
    assert infy.isin == "INE009A01021"
    assert infy.mic == "XNSE"
    assert infy.eligibility is True
    resolved = service.resolve("INFY", exchange="NSE")
    assert resolved.status == "RESOLVED"
    assert resolved.identity is not None
    assert resolved.identity.listing_id == "INE009A01021.XNSE"


def test_hdfcbank_and_wipro_nse() -> None:
    service = _service()
    hdfc = service.resolve("HDFCBANK", exchange="NSE")
    assert hdfc.status == "RESOLVED"
    assert hdfc.identity is not None
    assert hdfc.identity.isin == "INE040A01034"
    assert hdfc.identity.mic == "XNSE"
    wipro = service.resolve("Wipro", exchange="NSE")
    assert wipro.status == "RESOLVED"
    assert wipro.identity is not None
    assert wipro.identity.ticker == "WIPRO"
    assert wipro.identity.isin == "INE075A01022"


def test_dual_listed_without_exchange_is_ambiguous() -> None:
    service = _service()
    result = service.resolve("INFY")
    assert result.status == "AMBIGUOUS"
    assert result.identity is None
    mics = {item.mic for item in result.candidates}
    assert mics == {"XNSE", "XBOM"}


def test_unknown_ticker() -> None:
    service = _service()
    result = service.resolve("ZZZZZUNKNOWN")
    assert result.status == "UNKNOWN"
    assert result.identity is None
    search = service.search("ZZZZZUNKNOWN")
    assert search.status == "UNKNOWN"
    assert search.results == ()


def test_unsupported_warrant() -> None:
    service = _service()
    result = service.resolve("FAKEWARR", exchange="NSE")
    assert result.status == "UNSUPPORTED"


def test_vendor_shaped_rejected() -> None:
    service = _service()
    result = service.resolve("NSE_EQ|INE009A01021")
    assert result.status == "REJECTED"
    assert result.identity is None
    search = service.search("NSE_EQ|INE009A01021")
    assert search.status == "REJECTED"


def test_name_search_does_not_silently_select() -> None:
    service = _service()
    search = service.search("Infosys")
    assert search.status == "MATCHES"
    assert {item.mic for item in search.results} == {"XNSE", "XBOM"}


def test_default_catalog_contains_official_nse_universe() -> None:
    from data_engine.security_master.catalog import load_default_catalog

    catalog = load_default_catalog()
    assert len(catalog) > 2000
    tickers = {(item.ticker, item.mic) for item in catalog.all()}
    assert ("INFY", "XNSE") in tickers
    assert ("INFY", "XBOM") in tickers
    assert ("HDFCBANK", "XNSE") in tickers
    assert ("WIPRO", "XNSE") in tickers
    infy_nse = next(
        item for item in catalog.all() if item.ticker == "INFY" and item.mic == "XNSE"
    )
    assert infy_nse.isin == "INE009A01021"
    assert infy_nse.company_name == "Infosys Limited"
    assert catalog.get("INE009A01021", "XNSE") == infy_nse
    assert catalog.get("INE009A01021", "XBOM") is not None
    assert catalog.authority.source_type == "official_exchange_master"
    assert "vendor instrument" in catalog.authority.detail.lower()
