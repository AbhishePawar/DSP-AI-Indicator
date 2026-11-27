"""Historical public filing research using canonical financial engines.

This module does not authorize current investment recommendations
or replace authenticated production valuation inputs.
"""

from financial import FinancialEngine

from dsp_platform.research_retrieval.sec_statement_extractor import (
    extract_infosys_fy2025,
)

from dsp_platform.research_retrieval.public_statement_adapter import (
    build_public_financial_statements,
)


def analyze_public_filing(document):

    evidence = extract_infosys_fy2025(document)

    periods = sorted(evidence["periods"])

    statements = tuple(
        build_public_financial_statements(
            document,
            period_end=period,
        )
        for period in periods
    )

    analysis = FinancialEngine().analyze_financials(
        statements
    )

    return {
        "ticker": evidence["ticker"],
        "exchange": evidence["exchange"],
        "isin": evidence["isin"],
        "currency": evidence["currency"],
        "statement_basis": evidence["statement_basis"],
        "periods": periods,
        "source_url": evidence["source_url"],
        "content_hash": evidence["content_hash"],
        "evidence_class": "historical_public_filing",
        "authenticated_provider": False,
        "authorized_for_valuation": False,
        "financial_analysis": analysis.to_dict(),
        "limitations": [
            "Historical financial analysis only.",
            "Current market price not verified.",
            "Current outstanding shares not verified.",
            "Not authorized for production valuation.",
        ],
    }
