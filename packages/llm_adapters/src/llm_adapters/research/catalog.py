"""Qualification catalog: public identity rows, not a TCS-only path."""

from __future__ import annotations

from data_engine.security_identity import CatalogSecurityMaster, SecurityListing

# Public ISIN/MIC values. Not vendor instrument keys. Not TCS-only.
NSE_EQUITY = SecurityListing(
    ticker="INFY",
    exchange="NSE",
    isin="INE009A01021",
    mic="XNSE",
    company="Infosys Limited",
    security_type="EQUITY",
    listing_status="LISTED",
)
BSE_EQUITY = SecurityListing(
    ticker="INFY",
    exchange="BSE",
    isin="INE009A01021",
    mic="XBOM",
    company="Infosys Limited",
    security_type="EQUITY",
    listing_status="LISTED",
)
ARBITRARY_NSE = SecurityListing(
    ticker="HDFCBANK",
    exchange="NSE",
    isin="INE040A01034",
    mic="XNSE",
    company="HDFC Bank Limited",
    security_type="EQUITY",
    listing_status="LISTED",
)


def qualification_security_master() -> CatalogSecurityMaster:
    return CatalogSecurityMaster(
        listings=(NSE_EQUITY, BSE_EQUITY, ARBITRARY_NSE),
    )
