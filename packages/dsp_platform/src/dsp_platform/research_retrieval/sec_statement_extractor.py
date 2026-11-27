"""Deterministic extraction of the supported Infosys SEC filing.

This is a controlled pilot, not a universal SEC filing parser.
Extracted data remains public filing evidence, not authenticated
commercial-provider data.
"""

from __future__ import annotations

import re
from hashlib import sha256
from decimal import Decimal

from dsp_platform.research_retrieval.statement_integrity import (
    validate_statement_period,
)


class StatementExtractionError(ValueError):
    pass


EXPECTED_HASH = (
    "1ec5c267c3524581a15e27876df70ec8c"
    "672b6373ec00aa7f9832a131f2d0cbd"
)

EXPECTED_TEXT_HASH = "29c41ac0ae73157f3772ad32334f2242cfc0915926aa5bc6b9cad360ff9e0e7d"


EXPECTED_URL = (
    "https://www.sec.gov/Archives/edgar/data/"
    "1067491/000106749125000008/exv99w03.htm"
)


def parse_number(value):

    value = value.strip()

    if value in {"", "-", "–", "—"}:
        return None

    negative = value.startswith("(") and value.endswith(")")

    if negative:
        value = value[1:-1]

    value = value.strip()

    pattern = (
        r"(?:-?\d+|-?\d{1,3}(?:,\d{3})+)"
        r"(?:\.\d+)?"
    )

    if (
        not re.fullmatch(pattern, value)
        or (negative and value.startswith("-"))
    ):
        raise StatementExtractionError(
            "Invalid financial numeric cell"
        )

    number = Decimal(value.replace(",", ""))

    return -number if negative else number


def extract_row(
    section, label, columns,
    occurrence=0, expected_matches=1,
):

    matches = []

    for line in section.splitlines():

        if not line.lstrip().startswith("|"):
            continue

        cells = [
            cell.strip()
            for cell in line.strip().lstrip("|").split("|")
        ]

        if cells and cells[-1] == "":
            cells.pop()

        if not cells:
            continue

        if cells[0].casefold() != label.casefold():
            continue

        if len(cells) != columns + 1:
            continue

        matches.append(cells[1:])

    if not matches:
        return None

    if len(matches) != expected_matches:
        raise StatementExtractionError(
            f"Ambiguous financial row: {label}"
        )

    if not 0 <= occurrence < len(matches):
        raise StatementExtractionError(
            f"Invalid row occurrence: {label}"
        )

    return tuple(
        parse_number(value)
        for value in matches[occurrence]
    )


def extract_infosys_fy2025(document):

    if document.final_url != EXPECTED_URL:
        raise StatementExtractionError("Filing URL mismatch")

    if document.content_hash != EXPECTED_HASH:
        raise StatementExtractionError("Filing content changed")

    if document.status_code != 200:
        raise StatementExtractionError("Filing unavailable")

    text = document.text_content

    extracted_text_hash = sha256(
        text.encode("utf-8")
    ).hexdigest()

    if extracted_text_hash != EXPECTED_TEXT_HASH:
        raise StatementExtractionError(
            "Extracted filing text integrity mismatch"
        )

    lower = text.casefold()

    required = (
        "infosys limited",
        "l85110ka1981plc013115",
        "statement of consolidated audited results",
        "march 31, 2025",
        "ind-as",
        "in crore",
    )

    if not all(marker in lower for marker in required):
        raise StatementExtractionError(
            "Filing identity or accounting metadata missing"
        )

    income_start = lower.index(
        "statement of consolidated audited results"
    )

    income_end = lower.index(
        "1. notes",
        income_start,
    )

    balance_start = lower.index(
        "| assets |",
        income_end,
    )

    cash_start = lower.index(
        "4. audited consolidated statement of cash flows",
        balance_start,
    )

    cash_end = lower.index(
        "the disclosure is an extract of the audited "
        "consolidated statement of cash flows",
        cash_start,
    )

    income = text[income_start:income_end]
    balance = text[balance_start:cash_start]
    cash = text[cash_start:cash_end]

    income_header = re.sub(
        r"\s+", " ", income.casefold()
    )

    if (
        "year ended march 31," not in income_header
        or "| 2025 | 2024 | 2024 | 2025 | 2024"
        not in income_header
    ):
        raise StatementExtractionError(
            "Income statement column layout changed"
        )

    cash_header = re.sub(
        r"\s+", " ", cash.casefold()
    )

    if (
        "year ended march 31," not in cash_header
        or "| 2025 | 2024" not in cash_header
    ):
        raise StatementExtractionError(
            "Cash flow column layout changed"
        )

    income_fields = {
        "revenue": "Revenue from operations",
        "profit_before_tax": "Profit before tax",
        "net_income_total": "Profit for the period",
        "net_income_attributable_to_owners":
            "Owners of the company",
        "depreciation_and_amortization":
            "Depreciation and amortization expenses (1)",
        "finance_cost": "Finance cost",
        "eps_basic": "Basic (in per share)",
        "eps_diluted": "Diluted (in per share)",
    }

    balance_fields = {
        "cash_and_equivalents": "Cash and cash equivalents",
        "current_assets": "Total current assets",
        "total_assets": "Total Assets",
        "current_liabilities": "Total current liabilities",
        "non_current_liabilities":
            "Total non-current liabilities",
        "total_equity": "Total equity",
        "equity_attributable_to_owners":
            "Total equity attributable to equity holders of the Company",
        "equity_share_capital": "Equity share capital",
    }

    cash_fields = {
        "operating_cash_flow":
            "Net cash generated by operating activities",
        "capital_expenditure_reported":
            "Expenditure on property, plant and equipment and intangibles",
        "dividends_paid_reported": "Payment of dividends",
        "cash_end_of_period":
            "Cash and cash equivalents at the end of the period",
    }

    periods = {
        "2025-03-31": {},
        "2024-03-31": {},
    }

    def store(metric, values, indices, section, label):

        if values is None:
            return

        for period, index in zip(periods, indices):

            value = values[index]

            if value is None:
                continue

            periods[period][metric] = {
                "value": str(value),
                "unit": (
                    "INR per share"
                    if metric.startswith("eps_")
                    else "INR crore"
                ),
                "statement_basis": "consolidated",
                "section": section,
                "row_label": label,
                "source_column": index + 1,
            }

    profit_section_start = income.casefold().index(
        "profit attributable to:"
    )

    profit_section_end = income.casefold().index(
        "total comprehensive income attributable to:",
        profit_section_start,
    )

    profit_section = income[
        profit_section_start:profit_section_end
    ]

    for metric, label in income_fields.items():

        section_text = (
            profit_section
            if metric == "net_income_attributable_to_owners"
            else income
        )

        store(
            metric,
            extract_row(section_text, label, 5),
            (3, 4),
            "income_statement",
            label,
        )

    for metric, label in balance_fields.items():

        store(
            metric,
            extract_row(balance, label, 2),
            (0, 1),
            "balance_sheet",
            label,
        )

    for metric, label in cash_fields.items():

        store(
            metric,
            extract_row(cash, label, 2),
            (0, 1),
            "cash_flow",
            label,
        )

    for index, metric in enumerate((
        "non_current_lease_liabilities",
        "current_lease_liabilities",
    )):

        store(
            metric,
            extract_row(
                balance,
                "Lease liabilities",
                2,
                occurrence=index,
                expected_matches=2,
            ),
            (0, 1),
            "balance_sheet",
            "Lease liabilities",
        )

    required_metrics = {
        "revenue",
        "net_income_total",
        "total_assets",
        "total_equity",
        "cash_and_equivalents",
        "operating_cash_flow",
        "capital_expenditure_reported",
    }

    for period, metrics in periods.items():

        missing = required_metrics - metrics.keys()

        if missing:
            raise StatementExtractionError(
                f"Missing required rows for {period}: "
                f"{sorted(missing)}"
            )

    integrity = {
        period: validate_statement_period(metrics)
        for period, metrics in periods.items()
    }

    return {
        "integrity": integrity,
        "ticker": "INFY",
        "exchange": "NSE",
        "isin": "INE009A01021",
        "currency": "INR",
        "statement_basis": "consolidated",
        "source_url": document.final_url,
        "content_hash": document.content_hash,
        "extracted_text_hash": extracted_text_hash,
        "retrieved_at": document.fetched_at,
        "evidence_class": "public_filing_extraction",
        "authenticated_provider": False,
        "authorized_for_valuation": False,
        "periods": periods,
    }
