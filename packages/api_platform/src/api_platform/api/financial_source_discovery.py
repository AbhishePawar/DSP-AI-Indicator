"""Server-side bridge between AI discovery and DSP research retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from llm_adapters.web_research import OpenAIWebResearch

from dsp_platform.research_retrieval.models import (
    DiscoveredSource,
    SourceTier,
)

from dsp_platform.research_retrieval.governance import (
    RetrievalGovernance,
)

from dsp_platform.research_retrieval.url_safety import (
    validate_url_safety,
    UrlSafetyError,
)


SOURCE_DOMAINS = {
    "nseindia.com": "NSE",
    "bseindia.com": "BSE",
    "sec.gov": "SEC",
    "camskra.com": "CAMSKRA",
    "cdslindia.com": "CDSL",
    "screener.in": "SCREENER",
    "finance.yahoo.com": "YAHOO_FINANCE",
}


@dataclass(frozen=True, slots=True)
class FinancialDiscoveryResult:
    status: str
    sources: tuple[DiscoveredSource, ...] = ()
    unapproved_sources: tuple[DiscoveredSource, ...] = ()
    limitation: str | None = None


class FinancialSourceDiscovery:

    def __init__(self, *, discovery=None, governance=None):

        self.discovery = (
            discovery if discovery is not None
            else OpenAIWebResearch()
        )

        self.governance = (
            governance if governance is not None
            else RetrievalGovernance()
        )

    def discover_filings(
        self,
        ticker: str,
        *,
        exchange: str,
        fiscal_year: int,
    ) -> FinancialDiscoveryResult:

        ticker = str(ticker or "").strip().upper()
        exchange = str(exchange or "").strip().upper()

        if not re.fullmatch(r"[A-Z0-9&._-]{1,32}", ticker):

            return FinancialDiscoveryResult(
                status="unavailable",
                limitation="invalid_ticker",
            )

        if exchange not in {"NSE", "BSE"}:

            return FinancialDiscoveryResult(
                status="unavailable",
                limitation="unsupported_exchange",
            )

        if (
            type(fiscal_year) is not int
            or not 1990 <= fiscal_year <= 2100
        ):

            return FinancialDiscoveryResult(
                status="unavailable",
                limitation="invalid_fiscal_year",
            )

        query = (
            f"Find official audited annual financial statements "
            f"for the Indian listed instrument {ticker}, "
            f"exchange {exchange}, financial year ending "
            f"in {fiscal_year}. "
            "Prefer official exchange filings and issuer annual "
            "reports. Locate primary document URLs. "
            "Do not estimate financial figures. "
            "Return source citations."
        )

        result = self.discovery.discover(query)

        if result.status != "discovered":

            return FinancialDiscoveryResult(
                status="unavailable",
                limitation=result.limitation,
            )

        approved = []
        unapproved = []

        for item in result.sources:

            try:

                validate_url_safety(item.url)

                host = (
                    urlsplit(item.url).hostname or ""
                ).lower()

            except (UrlSafetyError, ValueError):
                continue

            publisher = next(
                (
                    source_name
                    for domain, source_name
                    in SOURCE_DOMAINS.items()
                    if host == domain
                    or host.endswith("." + domain)
                ),
                host,
            )

            decision = self.governance.evaluate_source(
                source=publisher,
                url=item.url,
                purpose="fundamental",
                publisher=publisher,
            )

            candidate = DiscoveredSource(
                url=item.url,
                publisher=publisher,
                title=item.title,
                source_tier=SourceTier.UNAPPROVED,
                discovered_by="native_web_research",
                metadata={
                    "requested_ticker": ticker,
                    "requested_exchange": exchange,
                    "requested_fiscal_year": str(fiscal_year),
                },
            )

            if decision.is_approved:
                approved.append(candidate)
            else:
                unapproved.append(candidate)

        return FinancialDiscoveryResult(
            status=(
                "discovered" if approved
                else "no_approved_sources"
            ),
            sources=tuple(approved),
            unapproved_sources=tuple(unapproved),
        )
