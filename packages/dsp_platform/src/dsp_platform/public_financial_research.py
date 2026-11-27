"""Controlled live acquisition of supported historical public filings.

Public research is kept separate from authenticated valuation data.
Unsupported instruments or reporting periods fail closed.
"""

from dsp_platform.public_filing_analysis import (
    analyze_public_filing,
)

from dsp_platform.research_retrieval.issuer_registry import (
    resolve_issuer,
)

from dsp_platform.research_retrieval.governance import (
    RetrievalGovernance,
)

from dsp_platform.research_retrieval.url_safety import (
    DefaultSafeHttpFetcher,
    UrlSafetyPolicy,
)

from dsp_platform.research_retrieval.sec_statement_extractor import (
    EXPECTED_URL,
)


class PublicFinancialResearchError(ValueError):
    pass


class PublicFinancialResearchService:

    def __init__(self, fetcher=None):

        self.fetcher = (
            fetcher
            if fetcher is not None
            else DefaultSafeHttpFetcher(
                policy=UrlSafetyPolicy(
                    timeout_seconds=15.0,
                    max_redirects=0,
                )
            )
        )

        self.governance = RetrievalGovernance()

    def analyze(self, ticker, *, exchange, fiscal_year):

        issuer = resolve_issuer(ticker, exchange)

        if issuer is None:
            raise PublicFinancialResearchError(
                "Unsupported issuer identity"
            )

        if (
            issuer.ticker != "INFY"
            or issuer.exchange != "NSE"
            or issuer.isin != "INE009A01021"
            or fiscal_year != 2025
        ):
            raise PublicFinancialResearchError(
                "No validated filing available for requested issuer and period"
            )

        decision = self.governance.evaluate_source(
            source="SEC",
            url=EXPECTED_URL,
            purpose="fundamental",
        )

        if not decision.is_approved:
            raise PublicFinancialResearchError(
                "Financial document source not approved"
            )

        document = self.fetcher.fetch(EXPECTED_URL)

        if (
            document.url != EXPECTED_URL
            or document.final_url != EXPECTED_URL
            or document.redirect_chain
        ):
            raise PublicFinancialResearchError(
                "Unexpected financial document destination"
            )

        result = analyze_public_filing(document)

        if (
            result["ticker"] != issuer.ticker
            or result["isin"] != issuer.isin
            or result["exchange"] != issuer.exchange
        ):
            raise PublicFinancialResearchError(
                "Financial document identity mismatch"
            )

        result["requested_fiscal_year"] = fiscal_year
        result["retrieved_at"] = document.fetched_at

        return result
