"""Approved-source whitelist. Secondary sources cannot become VERIFIED truth."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

__all__ = [
    "PRIMARY_HOST_SUFFIXES",
    "SECONDARY_HOST_SUFFIXES",
    "SourceClass",
    "SourcePolicy",
    "classify_source_url",
]

SourceClass = str  # "primary" | "secondary" | "forbidden" | "unknown"

PRIMARY_HOST_SUFFIXES: tuple[str, ...] = (
    "nseindia.com",
    "nse.co.in",
    "nsearchives.nseindia.com",
    "archives.nseindia.com",
    "bseindia.com",
    "sebi.gov.in",
    "mca.gov.in",
    "rbi.org.in",
    "nsdl.co.in",
    "nsdl.com",
    "cdslindia.com",
)

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

    def is_discovery_only(
        self, url: str | None, *, source_type: str | None = None
    ) -> bool:
        return self.classify(url, source_type=source_type) == "secondary"
