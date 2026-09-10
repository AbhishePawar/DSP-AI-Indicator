"""ISIN + MIC + series matching. Never ticker-only. NSE and BSE stay separate."""

from __future__ import annotations

from data_engine.official_research.models import UdiffCashRow
from data_engine.security_master.models import SecurityListing

__all__ = ["MIC_FOR_VENUE", "VENUE_FOR_MIC", "match_udiff_row"]

MIC_FOR_VENUE = {"NSE": "XNSE", "BSE": "XBOM"}
VENUE_FOR_MIC = {"XNSE": "NSE", "XBOM": "BSE"}

_EQUITY_SERIES = frozenset({"EQ", "BE", "A"})


def match_udiff_row(row: UdiffCashRow, listing: SecurityListing) -> bool:
    """Require ISIN + MIC + equity series. Ticker is corroboration only."""
    if row.isin != listing.isin:
        return False
    expected_mic = MIC_FOR_VENUE.get(row.venue)
    if expected_mic is None or listing.mic != expected_mic:
        return False
    if listing.security_type != "equity" or not listing.eligibility:
        return False
    if row.fin_instrm_tp and row.fin_instrm_tp.upper() not in {"STK", "EQ", "ES", ""}:
        return False
    if not row.scty_srs or row.scty_srs in _EQUITY_SERIES:
        return True
    if row.venue == "BSE" and row.scty_srs in {"A", "B", "T", "XT", "EQ"}:
        return True
    return bool(listing.series and row.scty_srs == listing.series.upper())
