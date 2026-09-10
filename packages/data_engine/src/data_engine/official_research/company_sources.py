"""Bounded company-source resolver. Search snippets are never evidence."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from data_engine.official_research.nse_primary import (
    NSE_ANNOUNCEMENTS_URL,
    NSE_FINANCIAL_RESULTS_URL,
    NSE_SHAREHOLDING_URL,
)
from data_engine.official_research.source_policy import classify_source_url
from data_engine.security_master.models import SecurityListing

__all__ = [
    "CompanySourceMap",
    "CompanySourceRegistry",
    "load_company_source_registry",
    "resolve_company_sources",
]


@dataclass(frozen=True, slots=True)
class CompanySourceMap:
    isin: str
    ticker: str
    official_domain: str | None
    investor_relations_url: str | None
    financial_results_url: str | None
    annual_report_url: str | None
    nse_announcements_url: str
    nse_financial_results_url: str
    nse_shareholding_url: str
    candidate_urls: tuple[str, ...] = ()


class CompanySourceRegistry:
    """ISIN-keyed official company domains. Empty means exchange filings only."""

    def __init__(self, rows: dict[str, str] | None = None) -> None:
        self._domains = {key.upper(): value.lower() for key, value in (rows or {}).items()}

    def official_domain(self, isin: str) -> str | None:
        return self._domains.get(isin.strip().upper())

    def allows(self, isin: str, url: str) -> bool:
        kind = classify_source_url(url)
        if kind == "primary":
            return True
        if kind in {"secondary", "forbidden", "unknown"}:
            if kind != "unknown":
                return False
        domain = self.official_domain(isin)
        if not domain:
            return False
        host = (urlparse(url).hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host == domain or host.endswith("." + domain)


def load_company_source_registry(path: Path | None = None) -> CompanySourceRegistry:
    target = path or (Path(__file__).resolve().parent / "data" / "official_company_sources.csv")
    if not target.exists():
        return CompanySourceRegistry()
    rows: dict[str, str] = {}
    with target.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            isin = str(row.get("isin") or "").strip().upper()
            domain = str(row.get("official_domain") or "").strip().lower()
            if isin and domain:
                rows[isin] = domain
    return CompanySourceRegistry(rows)


def resolve_company_sources(
    listing: SecurityListing,
    *,
    registry: CompanySourceRegistry | None = None,
    candidate_urls: tuple[str, ...] = (),
) -> CompanySourceMap:
    """Map identity → approved locators. Candidate URLs remain candidates."""
    symbol = listing.ticker
    registry = registry or CompanySourceRegistry()
    domain = registry.official_domain(listing.isin)
    validated: list[str] = []
    for url in candidate_urls:
        if registry.allows(listing.isin, url) or classify_source_url(url) == "primary":
            validated.append(url)
    ir = None
    if domain:
        ir = f"https://www.{domain}/investors"
    return CompanySourceMap(
        isin=listing.isin,
        ticker=listing.ticker,
        official_domain=domain,
        investor_relations_url=ir,
        financial_results_url=None,
        annual_report_url=None,
        nse_announcements_url=f"{NSE_ANNOUNCEMENTS_URL}?index=equities&symbol={symbol}",
        nse_financial_results_url=(
            f"{NSE_FINANCIAL_RESULTS_URL}?index=equities&symbol={symbol}&period=Annual"
        ),
        nse_shareholding_url=f"{NSE_SHAREHOLDING_URL}?index=equities&symbol={symbol}",
        candidate_urls=tuple(validated),
    )
