"""Regression tests for governed financial source discovery."""

from unittest.mock import Mock

import pytest

from api_platform.api.financial_source_discovery import (
    FinancialSourceDiscovery,
)

from llm_adapters.web_research import (
    WebResearchSource,
    WebResearchResult,
)

from dsp_platform.research_retrieval.models import SourceTier


def build_service(*urls):

    discovery = Mock()

    discovery.discover.return_value = WebResearchResult(
        status="discovered",
        sources=tuple(
            WebResearchSource(url=url, title="Annual report")
            for url in urls
        ),
    )

    return FinancialSourceDiscovery(
        discovery=discovery
    ), discovery


def run(service):

    return service.discover_filings(
        "INFY",
        exchange="NSE",
        fiscal_year=2026,
    )


def test_exchange_source_discovered():

    service, _ = build_service(
        "https://www.nseindia.com/financial-report"
    )

    result = run(service)

    assert result.status == "discovered"
    assert len(result.sources) == 1
    assert result.sources[0].publisher == "NSE"

    # Discovery never establishes financial authenticity.
    assert result.sources[0].source_tier is SourceTier.UNAPPROVED


def test_company_domain_requires_approval():

    service, _ = build_service(
        "https://www.infosys.com/report"
    )

    result = run(service)

    assert result.status == "no_approved_sources"
    assert not result.sources
    assert len(result.unapproved_sources) == 1


def test_domain_spoofing_rejected():

    service, _ = build_service(
        "https://nseindia.com.example.org/report"
    )

    result = run(service)

    assert not result.sources


def test_secondary_source_not_promoted():

    service, _ = build_service(
        "https://www.screener.in/company/INFY/"
    )

    result = run(service)

    assert len(result.sources) == 1

    assert (
        result.sources[0].source_tier
        is SourceTier.UNAPPROVED
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://www.nseindia.com/report",
        "https://127.0.0.1/report",
        "https://localhost/report",
        "file:///etc/passwd",
        "https://169.254.169.254/report",
    ],
)
def test_unsafe_destinations(url):

    service, _ = build_service(url)

    result = run(service)

    assert not result.sources
    assert not result.unapproved_sources


def test_invalid_ticker_does_not_contact_provider():

    service, provider = build_service()

    result = service.discover_filings(
        "invalid ticker input",
        exchange="NSE",
        fiscal_year=2026,
    )

    assert result.limitation == "invalid_ticker"

    provider.discover.assert_not_called()


def test_invalid_exchange():

    service, provider = build_service()

    result = service.discover_filings(
        "INFY",
        exchange="EQUITY",
        fiscal_year=2026,
    )

    assert result.limitation == "unsupported_exchange"

    provider.discover.assert_not_called()


def test_provider_failure():

    service, provider = build_service()

    provider.discover.return_value = WebResearchResult(
        status="unavailable",
        limitation="provider_http_503",
    )

    result = run(service)

    assert result.status == "unavailable"
    assert result.limitation == "provider_http_503"
