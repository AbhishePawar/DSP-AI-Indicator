"""P1-09 — deterministic CI investment fixture (evidence_class=test_fixture).

Seeds in-memory authenticated quote + statement adapters when explicitly
enabled. NEVER used as live vendor evidence. Refused when DSP_ENVIRONMENT
is production.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from data_engine import (
    FinancialStatementProvenance,
    InMemoryAuthenticatedQuoteAdapter,
    InMemoryAuthenticatedStatementAdapter,
    InMemoryShareCountAdapter,
    MarketQuoteProvenance,
    ShareCountProvenance,
    build_quote_from_mapping,
    build_share_count_from_mapping,
    build_statements_from_mapping,
)

__all__ = [
    "P109_FIXTURE_TICKER",
    "P109_EVIDENCE_CLASS",
    "p109_fixture_enabled",
    "seed_p109_memory_adapters",
    "build_p109_quote",
    "build_p109_statements",
    "build_p109_share_count",
]

P109_FIXTURE_TICKER = "DSPFIX"
P109_EVIDENCE_CLASS = "test_fixture"
_FIXED_RETRIEVED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


def p109_fixture_enabled(environ: dict[str, str] | None = None) -> bool:
    env = environ if environ is not None else os.environ
    if str(env.get("DSP_ENVIRONMENT") or "").strip().lower() == "production":
        return False
    return str(env.get("DSP_P109_E2E_FIXTURE") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def build_p109_quote(*, symbol: str = P109_FIXTURE_TICKER):
    return build_quote_from_mapping(
        symbol=symbol,
        payload={
            "exchange": "NYSE",
            "currency": "USD",
            "current_price": 25.0,
            "previous_close": 24.5,
            "open": 24.8,
            "high": 25.4,
            "low": 24.2,
            "market_cap": 2_500_000_000.0,
            "shares_outstanding": 100_000_000.0,
            "volume": 1_000_000,
        },
        provenance=MarketQuoteProvenance(
            provider_id="memory_authenticated_quote",
            provider_name="P1-09 CI Fixture Quote",
            source_type="licensed_vendor",
            retrieved_at=_FIXED_RETRIEVED,
            auth_mode="api_key",
            metadata={"evidence_class": P109_EVIDENCE_CLASS, "p109": "1"},
        ),
    )


def build_p109_statements(*, symbol: str = P109_FIXTURE_TICKER):
    return build_statements_from_mapping(
        symbol=symbol,
        payload={
            "identity": {
                "symbol": symbol,
                "exchange": "NYSE",
                "company_name": "DSP Fixture Corp",
                "currency": "USD",
            },
            "reporting_currency": "USD",
            "statement_basis": "consolidated",
            "unit_scale": "actual",
            "periods": [
                {
                    "period_type": "annual",
                    "fiscal_year": 2024,
                    "period_end": "2024-12-31",
                    "filing_date": "2025-02-15",
                    "reporting_currency": "USD",
                    "restated": False,
                    "statement_basis": "consolidated",
                    "unit_scale": "actual",
                    "income_statement": {
                        "revenue": 1_000_000_000.0,
                        "cost_of_revenue": 400_000_000.0,
                        "gross_profit": 600_000_000.0,
                        "operating_income": 300_000_000.0,
                        "ebit": 300_000_000.0,
                        "ebitda": 350_000_000.0,
                        "net_income": 210_000_000.0,
                        "eps_basic": 2.1,
                        "eps_diluted": 2.05,
                    },
                    "balance_sheet": {
                        "cash_and_equivalents": 150_000_000.0,
                        "current_assets": 450_000_000.0,
                        "total_assets": 1_000_000_000.0,
                        "current_liabilities": 200_000_000.0,
                        "total_liabilities": 400_000_000.0,
                        "total_equity": 600_000_000.0,
                        "total_debt": 250_000_000.0,
                        "long_term_debt": 200_000_000.0,
                    },
                    "cash_flow": {
                        "operating_cash_flow": 250_000_000.0,
                        "investing_cash_flow": -80_000_000.0,
                        "financing_cash_flow": -100_000_000.0,
                        "capital_expenditures": -80_000_000.0,
                        "free_cash_flow": 170_000_000.0,
                        "dividends_paid": -50_000_000.0,
                        "share_buybacks": -30_000_000.0,
                    },
                },
                {
                    "period_type": "annual",
                    "fiscal_year": 2023,
                    "period_end": "2023-12-31",
                    "reporting_currency": "USD",
                    "statement_basis": "consolidated",
                    "unit_scale": "actual",
                    "income_statement": {
                        "revenue": 900_000_000.0,
                        "net_income": 180_000_000.0,
                        "operating_income": 260_000_000.0,
                        "eps_basic": 1.8,
                    },
                    "balance_sheet": {
                        "total_assets": 920_000_000.0,
                        "total_liabilities": 380_000_000.0,
                        "total_equity": 540_000_000.0,
                        "total_debt": 230_000_000.0,
                    },
                    "cash_flow": {
                        "operating_cash_flow": 220_000_000.0,
                        "capital_expenditures": -70_000_000.0,
                        "free_cash_flow": 150_000_000.0,
                    },
                },
            ],
        },
        provenance=FinancialStatementProvenance(
            provider_id="memory_authenticated_statements",
            provider_name="P1-09 CI Fixture Statements",
            source_type="licensed_vendor",
            retrieved_at=_FIXED_RETRIEVED,
            auth_mode="api_key",
            metadata={"evidence_class": P109_EVIDENCE_CLASS, "p109": "1"},
        ),
    )


def build_p109_share_count(*, symbol: str = P109_FIXTURE_TICKER):
    """TEST-ONLY synthetic ShareCountSnapshot. Not a real provider or company."""
    return build_share_count_from_mapping(
        symbol=symbol,
        payload={
            "exchange": "NYSE",
            "shares": 100_000_000.0,
        },
        provenance=ShareCountProvenance(
            provider_id="memory_authenticated_share_count",
            provider_name="P1-09 CI Fixture Share Count",
            source_type="licensed_vendor",
            retrieved_at=_FIXED_RETRIEVED,
            auth_mode="api_key",
            metadata={"evidence_class": P109_EVIDENCE_CLASS, "p109": "1"},
        ),
    )


def seed_p109_memory_adapters(
    quote_adapter: Any,
    statement_adapter: Any,
    share_count_adapter: Any = None,
    *,
    symbol: str = P109_FIXTURE_TICKER,
) -> bool:
    """Put fixture rows into memory adapters. Returns True when seeded."""
    if not p109_fixture_enabled():
        return False
    seeded = False
    if isinstance(quote_adapter, InMemoryAuthenticatedQuoteAdapter):
        quote_adapter.put(build_p109_quote(symbol=symbol))
        seeded = True
    if isinstance(statement_adapter, InMemoryAuthenticatedStatementAdapter):
        statement_adapter.put(build_p109_statements(symbol=symbol))
        seeded = True
    if isinstance(share_count_adapter, InMemoryShareCountAdapter):
        share_count_adapter.put(build_p109_share_count(symbol=symbol))
        seeded = True
    return seeded
