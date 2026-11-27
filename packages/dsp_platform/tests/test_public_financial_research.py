"""Controlled public financial research integration tests."""

from dataclasses import replace
from pathlib import Path

import pytest

from dsp_platform.public_financial_research import (
    PublicFinancialResearchError,
    PublicFinancialResearchService,
)

from dsp_platform.research_retrieval.models import (
    FetchedDocument,
)

from dsp_platform.research_retrieval.sec_statement_extractor import (
    EXPECTED_URL,
    EXPECTED_HASH,
    StatementExtractionError,
)


@pytest.fixture
def document():

    path = (
        Path(__file__).parent
        / "fixtures"
        / "infosys_fy2025_sec.txt"
    )

    return FetchedDocument(
        url=EXPECTED_URL,
        final_url=EXPECTED_URL,
        status_code=200,
        content_type="text/html",
        text_content=path.read_text(),
        content_hash=EXPECTED_HASH,
        fetched_at="2026-11-27T10:00:00+00:00",
    )


class FakeFetcher:

    def __init__(self, document):

        self.document = document
        self.calls = []

    def fetch(self, url):

        self.calls.append(url)

        return self.document


def test_supported_public_financial_research(document):

    fetcher = FakeFetcher(document)

    service = PublicFinancialResearchService(
        fetcher=fetcher
    )

    result = service.analyze(
        "INFY",
        exchange="NSE",
        fiscal_year=2025,
    )

    assert fetcher.calls == [EXPECTED_URL]

    assert result["ticker"] == "INFY"
    assert result["isin"] == "INE009A01021"
    assert result["requested_fiscal_year"] == 2025

    assert result["authenticated_provider"] is False
    assert result["authorized_for_valuation"] is False

    assert result["financial_analysis"]


@pytest.mark.parametrize(
    "ticker,exchange,year",
    [
        ("TCS", "NSE", 2025),
        ("INFY", "BSE", 2025),
        ("INFY", "NSE", 2026),
        ("INFY", "NSE", 2023),
        ("UNKNOWN", "NSE", 2025),
    ],
)
def test_unsupported_research_does_not_fetch(
    document,
    ticker,
    exchange,
    year,
):

    fetcher = FakeFetcher(document)

    service = PublicFinancialResearchService(
        fetcher=fetcher
    )

    with pytest.raises(PublicFinancialResearchError):

        service.analyze(
            ticker,
            exchange=exchange,
            fiscal_year=year,
        )

    assert fetcher.calls == []


def test_unexpected_destination_rejected(document):

    modified = replace(
        document,
        final_url="https://example.com/financial.htm",
    )

    service = PublicFinancialResearchService(
        fetcher=FakeFetcher(modified)
    )

    with pytest.raises(PublicFinancialResearchError):

        service.analyze(
            "INFY",
            exchange="NSE",
            fiscal_year=2025,
        )


def test_modified_document_rejected(document):

    modified = replace(
        document,
        text_content=document.text_content + "\nmodified",
    )

    service = PublicFinancialResearchService(
        fetcher=FakeFetcher(modified)
    )

    with pytest.raises(StatementExtractionError):

        service.analyze(
            "INFY",
            exchange="NSE",
            fiscal_year=2025,
        )


def test_network_failure_not_replaced_with_fixture():

    class FailedFetcher:

        def fetch(self, url):

            raise TimeoutError("Simulated network failure")

    service = PublicFinancialResearchService(
        fetcher=FailedFetcher()
    )

    with pytest.raises(TimeoutError):

        service.analyze(
            "INFY",
            exchange="NSE",
            fiscal_year=2025,
        )
