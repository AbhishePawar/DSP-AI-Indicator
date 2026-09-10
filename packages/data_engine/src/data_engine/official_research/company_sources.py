"""Bounded company-source resolver. Search snippets are never evidence."""

from __future__ import annotations

import csv
import re
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
    "CANONICAL_STATEMENT_BASIS",
    "CompanySourceMap",
    "CompanySourceRecord",
    "CompanySourceRegistry",
    "host_of",
    "issuer_names_compatible",
    "load_company_source_registry",
    "resolve_company_sources",
]

CANONICAL_STATEMENT_BASIS = "consolidated"

_STOPWORDS = frozenset(
    {
        "limited",
        "ltd",
        "the",
        "and",
        "of",
        "india",
        "company",
        "corporation",
        "corp",
        "plc",
        "inc",
    }
)


@dataclass(frozen=True, slots=True)
class CompanySourceRecord:
    isin: str
    company_name: str
    official_domain: str
    investor_relations_url: str | None
    financial_results_url: str | None
    annual_reports_url: str | None
    source_verified_at: str
    verification_method: str
    status: str
    ticker_aliases: tuple[str, ...] = ()
    mic: str | None = None


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
    registry_status: str | None = None
    registry_issue: str | None = None
    verification_method: str | None = None


def host_of(url: str) -> str:
    host = (urlparse(str(url or "").strip()).hostname or "").lower()
    if host.startswith("www."):
        return host[4:]
    return host


def issuer_names_compatible(left: str, right: str) -> bool:
    """True when distinctive issuer tokens overlap. Never ticker-only."""
    a = _tokens(left)
    b = _tokens(right)
    if not a or not b:
        return False
    return bool(a & b)


def _tokens(name: str) -> set[str]:
    parts = re.findall(r"[a-z0-9]+", str(name or "").lower())
    return {part for part in parts if len(part) >= 3 and part not in _STOPWORDS}


class CompanySourceRegistry:
    """ISIN-keyed official company domains. Missing ISIN means exchange filings only."""

    def __init__(self, records: dict[str, CompanySourceRecord] | dict[str, str] | None = None) -> None:
        parsed: dict[str, CompanySourceRecord] = {}
        for key, value in (records or {}).items():
            if isinstance(value, CompanySourceRecord):
                parsed[key.upper()] = value
                continue
            domain = str(value or "").strip().lower()
            if not domain:
                continue
            parsed[key.upper()] = CompanySourceRecord(
                isin=key.upper(),
                company_name="",
                official_domain=domain,
                investor_relations_url=None,
                financial_results_url=None,
                annual_reports_url=None,
                source_verified_at="",
                verification_method="test_domain_only",
                status="ACTIVE",
            )
        self._records = parsed

    def record(self, isin: str) -> CompanySourceRecord | None:
        return self._records.get(str(isin or "").strip().upper())

    def official_domain(self, isin: str) -> str | None:
        item = self.record(isin)
        if item is None or item.status not in {"ACTIVE", "DOMAIN_ONLY"}:
            return None
        return item.official_domain

    def allows(self, isin: str, url: str) -> bool:
        kind = classify_source_url(url)
        if kind == "primary":
            return True
        if kind in {"secondary", "forbidden"}:
            return False
        item = self.record(isin)
        if item is None or item.status not in {"ACTIVE", "DOMAIN_ONLY"}:
            return False
        host = host_of(url)
        domain = item.official_domain.lower()
        return host == domain or host.endswith("." + domain)

    def records(self) -> tuple[CompanySourceRecord, ...]:
        return tuple(self._records.values())

    def matches_listing(self, listing: SecurityListing) -> tuple[bool, str | None]:
        item = self.record(listing.isin)
        if item is None:
            return True, None
        if item.status not in {"ACTIVE", "DOMAIN_ONLY"}:
            return False, f"registry status {item.status} for {listing.isin}"
        if item.isin != listing.isin:
            return False, "registry ISIN mismatch"
        if item.company_name and not issuer_names_compatible(
            item.company_name, listing.company_name
        ):
            return False, (
                f"registry company {item.company_name!r} does not match "
                f"listing {listing.company_name!r}"
            )
        return True, None

    def conflicts_other_issuer(self, text: str, listing: SecurityListing) -> bool:
        """True when another registered issuer is named and this listing is not."""
        hay = str(text or "")[:16000]
        ours = issuer_names_compatible(listing.company_name, hay)
        for item in self._records.values():
            if item.isin == listing.isin:
                continue
            if not item.company_name:
                continue
            if issuer_names_compatible(item.company_name, hay) and not ours:
                return True
        return False


def load_company_source_registry(path: Path | None = None) -> CompanySourceRegistry:
    target = path or (Path(__file__).resolve().parent / "data" / "official_company_sources.csv")
    if not target.exists():
        return CompanySourceRegistry()
    records: dict[str, CompanySourceRecord] = {}
    with target.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            isin = str(row.get("isin") or "").strip().upper()
            domain = str(row.get("official_domain") or "").strip().lower()
            status = str(row.get("status") or "ACTIVE").strip().upper() or "ACTIVE"
            if status not in {"ACTIVE", "DOMAIN_ONLY", "INACTIVE", "REVOKED"}:
                continue
            if not isin or not domain:
                continue
            aliases = tuple(
                part.strip().upper()
                for part in str(row.get("ticker_aliases") or "").split("|")
                if part.strip()
            )
            records[isin] = CompanySourceRecord(
                isin=isin,
                company_name=str(row.get("company_name") or "").strip(),
                official_domain=domain,
                investor_relations_url=_url(row.get("investor_relations_url")),
                financial_results_url=_url(row.get("financial_results_url")),
                annual_reports_url=_url(row.get("annual_reports_url")),
                source_verified_at=str(row.get("source_verified_at") or "").strip(),
                verification_method=str(row.get("verification_method") or "").strip(),
                status=status,
                ticker_aliases=aliases,
                mic=str(row.get("mic") or "").strip().upper() or None,
            )
    return CompanySourceRegistry(records)


def _url(raw: object) -> str | None:
    text = str(raw or "").strip()
    if not text.startswith("http://") and not text.startswith("https://"):
        return None
    return text


def resolve_company_sources(
    listing: SecurityListing,
    *,
    registry: CompanySourceRegistry | None = None,
    candidate_urls: tuple[str, ...] = (),
) -> CompanySourceMap:
    """Map identity → approved locators. Candidate URLs remain candidates."""
    symbol = listing.ticker
    registry = registry or load_company_source_registry()
    ok, issue = registry.matches_listing(listing)
    item = registry.record(listing.isin)
    domain = None if not ok else registry.official_domain(listing.isin)
    validated: list[str] = []
    if ok:
        for url in candidate_urls:
            if registry.allows(listing.isin, url) or classify_source_url(url) == "primary":
                validated.append(url)
        if item is not None:
            for url in (
                item.annual_reports_url,
                item.financial_results_url,
                item.investor_relations_url,
            ):
                if url and url not in validated and registry.allows(listing.isin, url):
                    validated.append(url)
    return CompanySourceMap(
        isin=listing.isin,
        ticker=listing.ticker,
        official_domain=domain,
        investor_relations_url=None if item is None or not ok else item.investor_relations_url,
        financial_results_url=None if item is None or not ok else item.financial_results_url,
        annual_report_url=None if item is None or not ok else item.annual_reports_url,
        nse_announcements_url=f"{NSE_ANNOUNCEMENTS_URL}?index=equities&symbol={symbol}",
        nse_financial_results_url=(
            f"{NSE_FINANCIAL_RESULTS_URL}?index=equities&symbol={symbol}&period=Annual"
        ),
        nse_shareholding_url=f"{NSE_SHAREHOLDING_URL}?index=equities&symbol={symbol}",
        candidate_urls=tuple(validated),
        registry_status=None if item is None else item.status,
        registry_issue=issue,
        verification_method=None if item is None or not ok else item.verification_method,
    )
