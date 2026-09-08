"""Load the official Security Master universe.

Authority:
  * NSE EQUITY_L.csv (official NSE equity master, ISIN + ticker + name)
  * BSE dual listings of the same ISIN (MIC XBOM) for Nifty-50 constituents

Does not load Upstox, Yahoo, FMP, or any vendor instrument key.
"""

from __future__ import annotations

import csv
from pathlib import Path

from data_engine.security_master.models import (
    EXCHANGE_MIC,
    SecurityListing,
    SecurityMasterAuthority,
    UNSUPPORTED_SECURITY_TYPES,
)

__all__ = [
    "NSE_EQUITY_L_URL",
    "SECURITY_MASTER_RETRIEVED_AT",
    "SecurityMasterCatalog",
    "default_authority",
    "load_default_catalog",
]

NSE_EQUITY_L_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
SECURITY_MASTER_RETRIEVED_AT = "2026-09-09T00:00:00+00:00"

_DATA_DIR = Path(__file__).resolve().parent / "data"
_NSE_CSV = _DATA_DIR / "nse_equity_l.csv"
_BSE_CSV = _DATA_DIR / "bse_dual_listings.csv"

_EQUITY_SERIES = frozenset({"EQ", "BE"})
_EQUITY_TYPES = frozenset({"equity"})


def _cell(row: dict[str, str], name: str) -> str:
    for key, value in row.items():
        if key.strip() == name:
            return str(value or "").strip()
    return ""


def _series_security_type(series: str) -> tuple[str, bool]:
    cleaned = series.strip().upper()
    if cleaned in _EQUITY_SERIES or cleaned == "BZ":
        return "equity", True
    lowered = cleaned.lower()
    if lowered in UNSUPPORTED_SECURITY_TYPES:
        return lowered, False
    if cleaned in {"W", "WR", "WARRANT"}:
        return "warrant", False
    if cleaned in {"GB", "GS", "N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "N9", "NA", "NB", "NC", "ND", "NE", "NL", "Y"}:
        return "bond", False
    return "unsupported", False


def default_authority() -> SecurityMasterAuthority:
    return SecurityMasterAuthority(
        source="NSE EQUITY_L + BSE dual listings of the same ISIN",
        source_type="official_exchange_master",
        retrieved_at=SECURITY_MASTER_RETRIEVED_AT,
        detail=(
            f"NSE listings from official {NSE_EQUITY_L_URL}. "
            "BSE rows reuse the NSE ISIN with MIC XBOM for documented "
            "dual-listed Nifty-50 constituents. Not a vendor instrument feed."
        ),
    )


def _nse_listing(row: dict[str, str]) -> SecurityListing | None:
    ticker = _cell(row, "SYMBOL").upper()
    name = _cell(row, "NAME OF COMPANY")
    isin = _cell(row, "ISIN NUMBER").upper()
    series = _cell(row, "SERIES").upper()
    if not ticker or not name or not isin:
        return None
    if not isin.startswith("IN") or len(isin) != 12:
        return None
    security_type, eligible = _series_security_type(series)
    return SecurityListing(
        ticker=ticker,
        company_name=name,
        isin=isin,
        exchange="NSE",
        mic=EXCHANGE_MIC["NSE"],
        security_type=security_type,
        eligibility=eligible and security_type in _EQUITY_TYPES,
        series=series or None,
    )


def _bse_listing(row: dict[str, str]) -> SecurityListing | None:
    ticker = _cell(row, "SYMBOL").upper()
    name = _cell(row, "NAME OF COMPANY")
    isin = _cell(row, "ISIN NUMBER").upper()
    series = _cell(row, "SERIES").upper()
    exchange = (_cell(row, "EXCHANGE") or "BSE").upper()
    mic = (_cell(row, "MIC") or EXCHANGE_MIC.get(exchange, "")).upper()
    if not ticker or not name or not isin or not mic:
        return None
    security_type, eligible = _series_security_type(series or "EQ")
    return SecurityListing(
        ticker=ticker,
        company_name=name,
        isin=isin,
        exchange=exchange,
        mic=mic,
        security_type=security_type,
        eligibility=eligible and security_type in _EQUITY_TYPES,
        series=series or None,
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class SecurityMasterCatalog:
    """In-memory official listing universe keyed by ISIN+MIC."""

    def __init__(
        self,
        listings: tuple[SecurityListing, ...],
        *,
        authority: SecurityMasterAuthority | None = None,
    ) -> None:
        unique: dict[str, SecurityListing] = {}
        for listing in listings:
            unique[listing.listing_id] = listing
        self._listings = tuple(
            sorted(unique.values(), key=lambda item: (item.ticker, item.mic))
        )
        self.authority = authority or default_authority()

    @classmethod
    def from_listings(
        cls,
        listings: list[SecurityListing] | tuple[SecurityListing, ...],
        *,
        authority: SecurityMasterAuthority | None = None,
    ) -> SecurityMasterCatalog:
        return cls(tuple(listings), authority=authority)

    def extend(self, extra: tuple[SecurityListing, ...]) -> SecurityMasterCatalog:
        return SecurityMasterCatalog(
            self._listings + extra, authority=self.authority
        )

    def all(self) -> tuple[SecurityListing, ...]:
        return self._listings

    def __len__(self) -> int:
        return len(self._listings)


def load_default_catalog() -> SecurityMasterCatalog:
    if not _NSE_CSV.is_file():
        msg = f"NSE Security Master snapshot missing: {_NSE_CSV}"
        raise FileNotFoundError(msg)
    listings: list[SecurityListing] = []
    for row in _read_csv(_NSE_CSV):
        item = _nse_listing(row)
        if item is not None:
            listings.append(item)
    if _BSE_CSV.is_file():
        for row in _read_csv(_BSE_CSV):
            item = _bse_listing(row)
            if item is not None:
                listings.append(item)
    return SecurityMasterCatalog(tuple(listings), authority=default_authority())
