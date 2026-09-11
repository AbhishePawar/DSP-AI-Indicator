"""Approved-source whitelist. Secondary sources cannot become VERIFIED truth.

Screener is Tier-1C approved research: it may CROSS_CHECK a primary
value. It cannot itself become VERIFIED or be retrieved as truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

__all__ = [
    "APPROVED_RESEARCH_HOST_SUFFIXES",
    "FIELD_AUTHORITY_CHAIN",
    "PRIMARY_HOST_SUFFIXES",
    "SECONDARY_HOST_SUFFIXES",
    "SourceClass",
    "SourcePolicy",
    "classify_source_url",
    "field_authority_chain",
    "record_source_clash",
    "source_authority_rank",
]

SourceClass = str  # primary | approved_research | secondary | forbidden | unknown

PRIMARY_HOST_SUFFIXES: tuple[str, ...] = (
    "nseindia.com",
    "nseindia.in",
    "nse.co.in",
    "nsearchives.nseindia.com",
    "archives.nseindia.com",
    "mcp.nseindia.in",
    "bseindia.com",
    "sebi.gov.in",
    "mca.gov.in",
    "rbi.org.in",
    "nsdl.co.in",
    "nsdl.com",
    "cdslindia.com",
)

APPROVED_RESEARCH_HOST_SUFFIXES: tuple[str, ...] = ("screener.in",)

# Company IR hosts are primary only when the caller marks source_type company_ir.
# Host allowlist here is exchange/regulator. Company sites are validated by
# source_type == "company_ir" plus an https URL, not a global crawl of the web.

SECONDARY_HOST_SUFFIXES: tuple[str, ...] = (
    "finance.yahoo.com",
    "yahoo.com",
    "ibef.org",
)

_FORBIDDEN_HINTS: tuple[str, ...] = (
    "yfinance",
    "financialmodelingprep.com",
    "fmpcloud.io",
    "eodhd.com",
    "upstox.com",
    "alphavantage.co",
)


def _host(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        return host[4:]
    return host


def _matches(host: str, suffixes: tuple[str, ...]) -> bool:
    return any(host == suffix or host.endswith("." + suffix) for suffix in suffixes)


def classify_source_url(
    url: str | None, *, source_type: str | None = None
) -> SourceClass:
    text = str(url or "").strip()
    if not text:
        return "unknown"
    lowered = text.lower()
    if any(hint in lowered for hint in _FORBIDDEN_HINTS):
        return "forbidden"
    host = _host(text)
    if not host:
        return "unknown"
    if _matches(host, PRIMARY_HOST_SUFFIXES):
        return "primary"
    if _matches(host, APPROVED_RESEARCH_HOST_SUFFIXES):
        return "approved_research"
    if _matches(host, SECONDARY_HOST_SUFFIXES):
        return "secondary"
    if source_type == "company_ir" and lowered.startswith("https://"):
        return "primary"
    return "unknown"


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    """Enforces primary vs secondary promotion rules."""

    def classify(
        self, url: str | None, *, source_type: str | None = None
    ) -> SourceClass:
        return classify_source_url(url, source_type=source_type)

    def may_verify(self, url: str | None, *, source_type: str | None = None) -> bool:
        return self.classify(url, source_type=source_type) == "primary"

    def may_cross_check(
        self, url: str | None, *, source_type: str | None = None
    ) -> bool:
        return self.classify(url, source_type=source_type) == "approved_research"

    def is_discovery_only(
        self, url: str | None, *, source_type: str | None = None
    ) -> bool:
        return self.classify(url, source_type=source_type) == "secondary"


FIELD_AUTHORITY_CHAIN: dict[str, tuple[str, ...]] = {
    "price": (
        "nse_bse",
        "company",
        "screener",
        "yahoo_ibef",
        "ai",
    ),
    "financials": (
        "company_or_exchange_filing",
        "screener",
        "yahoo_ibef",
        "ai",
    ),
    "shares": (
        "nse_bse_regulator_company",
        "screener",
        "yahoo_ibef",
        "ai",
    ),
    "corporate_actions": (
        "nse_bse_regulator",
        "company",
        "screener",
        "yahoo_ibef",
        "ai",
    ),
}


def field_authority_chain(field: str) -> tuple[str, ...]:
    group = _FIELD_GROUP.get(field, "financials")
    if field in {"corporate_actions", "bonus", "split", "buyback"}:
        group = "corporate_actions"
    return FIELD_AUTHORITY_CHAIN[group]


_FIELD_GROUP = {
    "eod_close": "price",
    "last_price": "price",
    "revenue": "financials",
    "operating_profit": "financials",
    "ebit": "financials",
    "net_income": "financials",
    "equity": "financials",
    "cash": "financials",
    "cfo": "financials",
    "capex": "financials",
    "debt": "financials",
    "total_assets": "financials",
    "total_liabilities": "financials",
    "shares_outstanding": "shares",
}

_CLASS_ORDER: tuple[str, ...] = (
    "primary",
    "approved_research",
    "secondary",
    "unknown",
    "forbidden",
)

_TYPE_ORDER: tuple[str, ...] = (
    "exchange_eod",
    "regulator",
    "company_ir",
    "approved_research",
    "secondary",
    "llm",
    "agent_claim",
)


def source_authority_rank(
    field: str,
    source_class: str,
    *,
    source_type: str | None = None,
) -> tuple[int, int]:
    """Lower tuple is stronger. Field-specific: filings treat NSE and company IR equally."""
    group = _FIELD_GROUP.get(field, "financials")
    class_rank = (
        _CLASS_ORDER.index(source_class) if source_class in _CLASS_ORDER else 99
    )
    kind = str(source_type or "")
    if source_class == "primary" and kind in {"exchange_eod", "regulator"}:
        type_rank = 0
    elif source_class == "primary" and kind == "company_ir":
        type_rank = 0 if group == "financials" else 1
    elif source_class == "approved_research":
        type_rank = 2
    else:
        type_rank = _TYPE_ORDER.index(kind) if kind in _TYPE_ORDER else 9
    return (class_rank, type_rank)


def record_source_clash(
    *,
    field: str,
    primary_url: str,
    primary_value: str,
    research_url: str,
    research_value: str,
) -> dict[str, object]:
    """Record a Screener/primary clash. Primary wins. Never silent overwrite."""
    if str(primary_value) == str(research_value):
        return {
            "field": field,
            "cross_check": "PASS",
            "winner": "primary",
            "silent_overwrite": False,
            "stronger_source": primary_url,
            "stronger_value": primary_value,
            "weaker_source": research_url,
            "weaker_value": research_value,
        }
    return {
        "field": field,
        "cross_check": "CONFLICT",
        "winner": "primary",
        "recorded_as": "CONFLICT",
        "silent_overwrite": False,
        "stronger_source": primary_url,
        "stronger_value": primary_value,
        "weaker_source": research_url,
        "weaker_value": research_value,
    }
