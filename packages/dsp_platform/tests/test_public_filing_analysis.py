"""Public filing to financial engine integration tests."""

from pathlib import Path

import pytest

from financial import FinancialEngine

from dsp_platform.research_retrieval.models import (
    FetchedDocument,
)

from dsp_platform.research_retrieval.sec_statement_extractor import (
    EXPECTED_URL,
    EXPECTED_HASH,
)

from dsp_platform.research_retrieval.public_statement_adapter import (
    PublicStatementError,
    build_public_financial_statements,
)

from dsp_platform.public_filing_analysis import (
    analyze_public_filing,
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


def test_financial_scale_conversion(document):

    result = build_public_financial_statements(
        document,
        period_end="2025-03-31",
    )

    assert result.income_statement.revenue == 1629900000000

    assert result.balance_sheet.total_assets == 1489030000000

    assert result.income_statement.eps == 64.50


def test_complete_balance_sheet_mapping(document):

    result = build_public_financial_statements(
        document,
        period_end="2025-03-31",
    )

    bs = result.balance_sheet

    assert bs.current_assets == 970990000000

    assert bs.current_liabilities == 428500000000

    assert bs.lease_liabilities == 82270000000

    assert bs.share_capital == 20730000000


def test_missing_financial_data_not_fabricated(document):

    result = build_public_financial_statements(
        document,
        period_end="2025-03-31",
    )

    assert result.income_statement.weighted_shares is None

    assert result.balance_sheet.long_term_debt is None

    assert result.balance_sheet.short_term_debt is None

    assert result.income_statement.ebit is None


def test_fcf_not_mislabeled_as_reported(document):

    result = build_public_financial_statements(
        document,
        period_end="2025-03-31",
    )

    assert result.cash_flow.free_cash_flow is None

    assert result.cash_flow.operating_cash_flow == 356940000000

    assert result.cash_flow.capex == -22370000000


def test_prior_year_conversion(document):

    result = build_public_financial_statements(
        document,
        period_end="2024-03-31",
    )

    assert result.income_statement.revenue == 1536700000000

    assert result.balance_sheet.current_assets == 894320000000

    assert result.income_statement.eps == 63.39


def test_unavailable_period_rejected(document):

    with pytest.raises(PublicStatementError):

        build_public_financial_statements(
            document,
            period_end="2026-03-31",
        )


def test_canonical_financial_engine_execution(document):

    statements = build_public_financial_statements(
        document,
        period_end="2025-03-31",
    )

    analysis = FinancialEngine().analyze_financials(
        statements
    )

    assert analysis is not None


def test_multi_period_financial_analysis(document):

    result = analyze_public_filing(document)

    assert result["periods"] == [
        "2024-03-31",
        "2025-03-31",
    ]

    assert result["financial_analysis"]["trends"] is not None

    assert result["authenticated_provider"] is False

    assert result["authorized_for_valuation"] is False


def test_public_filing_provenance(document):

    result = analyze_public_filing(document)

    assert result["ticker"] == "INFY"

    assert result["isin"] == "INE009A01021"

    assert result["source_url"] == EXPECTED_URL

    assert result["content_hash"] == EXPECTED_HASH

    assert result["evidence_class"] == "historical_public_filing"
