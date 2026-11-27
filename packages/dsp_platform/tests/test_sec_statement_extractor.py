"""Deterministic public financial filing regression tests."""

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from dsp_platform.research_retrieval.models import (
    FetchedDocument,
)

from dsp_platform.research_retrieval.sec_statement_extractor import (
    EXPECTED_HASH,
    EXPECTED_TEXT_HASH,
    extract_row,
    EXPECTED_URL,
    StatementExtractionError,
    extract_infosys_fy2025,
    parse_number,
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


def test_extract_actual_financial_statement(document):

    result = extract_infosys_fy2025(document)

    assert len(result["periods"]) == 2

    assert sum(
        len(fields)
        for fields in result["periods"].values()
    ) == 44

    assert result["currency"] == "INR"
    assert result["statement_basis"] == "consolidated"


@pytest.mark.parametrize(
    "period,metric,expected",
    [
        ("2025-03-31", "revenue", "162990"),
        ("2024-03-31", "revenue", "153670"),
        ("2025-03-31", "net_income_total", "26750"),
        ("2025-03-31", "net_income_attributable_to_owners", "26713"),
        ("2025-03-31", "total_assets", "148903"),
        ("2025-03-31", "total_equity", "96203"),
        ("2025-03-31", "operating_cash_flow", "35694"),
        ("2025-03-31", "capital_expenditure_reported", "-2237"),
        ("2025-03-31", "cash_and_equivalents", "24455"),
        ("2025-03-31", "eps_basic", "64.50"),
        ("2024-03-31", "operating_cash_flow", "25210"),
        ("2024-03-31", "capital_expenditure_reported", "-2201"),
        ("2024-03-31", "total_assets", "137814"),
        ("2024-03-31", "total_equity", "88461"),
    ],
)
def test_reported_values(document, period, metric, expected):

    result = extract_infosys_fy2025(document)

    actual = result["periods"][period][metric]["value"]

    assert Decimal(actual) == Decimal(expected)


def test_public_evidence_not_authenticated(document):

    result = extract_infosys_fy2025(document)

    assert result["authenticated_provider"] is False
    assert result["authorized_for_valuation"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("content_hash", "invalid-hash"),
        ("final_url", "https://example.com/filing"),
        ("status_code", 403),
    ],
)
def test_invalid_document_rejected(document, field, value):

    with pytest.raises(StatementExtractionError):

        extract_infosys_fy2025(
            replace(document, **{field: value})
        )


def test_wrong_company_rejected(document):

    modified = document.text_content.replace(
        "Infosys Limited", "Unknown Limited"
    )

    with pytest.raises(StatementExtractionError):

        extract_infosys_fy2025(
            replace(document, text_content=modified)
        )


def test_missing_revenue_rejected(document):

    modified = document.text_content.replace(
        "Revenue from operations",
        "Unknown revenue row",
    )

    with pytest.raises(StatementExtractionError):

        extract_infosys_fy2025(
            replace(document, text_content=modified)
        )


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("162,990", Decimal("162990")),
        ("(2,237)", Decimal("-2237")),
        ("64.50", Decimal("64.50")),
        ("0", Decimal("0")),
        ("-", None),
        ("", None),
    ],
)
def test_numeric_parsing(raw, expected):

    assert parse_number(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["unknown", "NaN", "Infinity", "100 USD"],
)
def test_invalid_numbers(raw):

    with pytest.raises(StatementExtractionError):

        parse_number(raw)


def test_missing_share_count_not_invented(document):

    result = extract_infosys_fy2025(document)

    for metrics in result["periods"].values():

        assert "shares_outstanding" not in metrics
        assert "total_debt" not in metrics


@pytest.mark.parametrize(
    "raw",
    [
        "1,,000",
        "12,34",
        "1,2,3",
        "(-100)",
        "100,",
        ",100",
        "1,000.2.3",
    ],
)
def test_malformed_financial_number_rejected(raw):

    with pytest.raises(StatementExtractionError):

        parse_number(raw)


def test_duplicate_revenue_rejected(document):

    lines = document.text_content.splitlines()

    index = next(
        i for i, line in enumerate(lines)
        if line.startswith("| Revenue from operations |")
    )

    lines.insert(index + 1, lines[index])

    changed = replace(
        document,
        text_content="\n".join(lines),
    )

    with pytest.raises(
        StatementExtractionError,
        match="Extracted filing text integrity mismatch",
    ):

        extract_infosys_fy2025(changed)


def test_profit_not_comprehensive_income(document):

    result = extract_infosys_fy2025(document)

    record = result["periods"]["2025-03-31"][
        "net_income_attributable_to_owners"
    ]

    assert Decimal(record["value"]) == Decimal("26713")

    assert Decimal(record["value"]) != Decimal("27167")


def test_integrity_runs_during_extraction(document):

    result = extract_infosys_fy2025(document)

    for period in ("2025-03-31", "2024-03-31"):

        integrity = result["integrity"][period]

        assert integrity["balance_sheet_reconciled"]
        assert integrity["closing_cash_reconciled"]
        assert integrity["authorized_for_valuation"] is False


def test_duplicate_lease_rows_rejected(document):

    lines = document.text_content.splitlines()

    index = next(
        i for i, line in enumerate(lines)
        if line.startswith("| Lease liabilities |")
    )

    lines.insert(index + 1, lines[index])

    changed = replace(
        document,
        text_content="\n".join(lines),
    )

    with pytest.raises(
        StatementExtractionError,
        match="Extracted filing text integrity mismatch",
    ):

        extract_infosys_fy2025(changed)



def test_extracted_text_hash_preserved(document):

    result = extract_infosys_fy2025(document)

    assert (
        result["extracted_text_hash"]
        == EXPECTED_TEXT_HASH
    )


def test_modified_financial_value_rejected(document):

    modified = document.text_content.replace(
        "162,990",
        "999,999",
        1,
    )

    assert modified != document.text_content

    with pytest.raises(
        StatementExtractionError,
        match="Extracted filing text integrity mismatch",
    ):

        extract_infosys_fy2025(
            replace(
                document,
                text_content=modified,
            )
        )


def test_duplicate_row_parser_rejection():

    section = chr(10).join([
        "| Revenue | 100 | 90 |",
        "| Revenue | 100 | 90 |",
    ])

    assert len(section.splitlines()) == 2

    with pytest.raises(
        StatementExtractionError,
        match="Ambiguous financial row",
    ):

        extract_row(
            section,
            "Revenue",
            2,
        )
