"""Frozen official exchange locators for the DSP Security Master.

URLs are the NSE "Securities available for trading" archive files and the
BSE List of Scrips JSON API, both retrieved live during SIMPLE-13 forensic
on 2026-09-07. Callers must not accept arbitrary URLs.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "BSE_LIST_SCRIPS_REFERER",
    "NSE_SECURITIES_PAGE",
    "SECURITY_MASTER_HOSTS",
    "OfficialSource",
    "OFFICIAL_SOURCES",
]

NSE_SECURITIES_PAGE = (
    "https://www.nseindia.com/market-data/securities-available-for-trading"
)
BSE_LIST_SCRIPS_REFERER = "https://www.bseindia.com/corporates/List_Scrips.html"

SECURITY_MASTER_HOSTS = frozenset(
    {
        "nseindia.com",
        "www.nseindia.com",
        "nsearchives.nseindia.com",
        "bseindia.com",
        "www.bseindia.com",
        "api.bseindia.com",
    }
)


@dataclass(frozen=True, slots=True)
class OfficialSource:
    source_id: str
    exchange: str
    document_kind: str
    uri: str
    referer: str
    accept: str
    required: bool


OFFICIAL_SOURCES: tuple[OfficialSource, ...] = (
    OfficialSource(
        source_id="nse_equity",
        exchange="NSE",
        document_kind="equity",
        uri="https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
        referer=NSE_SECURITIES_PAGE,
        accept="text/csv,text/plain,*/*",
        required=True,
    ),
    OfficialSource(
        source_id="nse_sme",
        exchange="NSE",
        document_kind="sme_equity",
        uri="https://nsearchives.nseindia.com/emerge/corporates/content/SME_EQUITY_L.csv",
        referer=NSE_SECURITIES_PAGE,
        accept="text/csv,text/plain,*/*",
        required=True,
    ),
    OfficialSource(
        source_id="nse_etf",
        exchange="NSE",
        document_kind="etf",
        uri="https://nsearchives.nseindia.com/content/equities/eq_etfseclist.csv",
        referer=NSE_SECURITIES_PAGE,
        accept="text/csv,text/plain,*/*",
        required=True,
    ),
    OfficialSource(
        source_id="nse_reit",
        exchange="NSE",
        document_kind="reit",
        uri="https://nsearchives.nseindia.com/content/equities/REITS_L.csv",
        referer=NSE_SECURITIES_PAGE,
        accept="text/csv,text/plain,*/*",
        required=True,
    ),
    OfficialSource(
        source_id="nse_invit",
        exchange="NSE",
        document_kind="invit",
        uri="https://nsearchives.nseindia.com/content/equities/INVITS_L.csv",
        referer=NSE_SECURITIES_PAGE,
        accept="text/csv,text/plain,*/*",
        required=True,
    ),
    OfficialSource(
        source_id="nse_preference",
        exchange="NSE",
        document_kind="preference",
        uri="https://nsearchives.nseindia.com/content/equities/PREF.csv",
        referer=NSE_SECURITIES_PAGE,
        accept="text/csv,text/plain,*/*",
        required=True,
    ),
    OfficialSource(
        source_id="nse_warrant",
        exchange="NSE",
        document_kind="warrant",
        uri="https://nsearchives.nseindia.com/content/equities/WARRANT.csv",
        referer=NSE_SECURITIES_PAGE,
        accept="text/csv,text/plain,*/*",
        required=True,
    ),
    OfficialSource(
        source_id="bse_active",
        exchange="BSE",
        document_kind="equity_active",
        uri=(
            "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
            "?Group=&Scripcode=&industry=&segment=Equity&status=Active"
        ),
        referer=BSE_LIST_SCRIPS_REFERER,
        accept="application/json,text/plain,*/*",
        required=True,
    ),
    OfficialSource(
        source_id="bse_suspended",
        exchange="BSE",
        document_kind="equity_suspended",
        uri=(
            "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
            "?Group=&Scripcode=&industry=&segment=Equity&status=Suspended"
        ),
        referer=BSE_LIST_SCRIPS_REFERER,
        accept="application/json,text/plain,*/*",
        required=True,
    ),
    OfficialSource(
        source_id="bse_delisted",
        exchange="BSE",
        document_kind="equity_delisted",
        uri=(
            "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
            "?Group=&Scripcode=&industry=&segment=Equity&status=Delisted"
        ),
        referer=BSE_LIST_SCRIPS_REFERER,
        accept="application/json,text/plain,*/*",
        required=True,
    ),
)
