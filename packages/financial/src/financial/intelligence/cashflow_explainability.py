"""Explainability for Cash Flow Intelligence (F2.4)."""

from __future__ import annotations

from financial.intelligence.income_explainability import (
    MetricExplanation,
    build_explanation,
)

__all__ = [
    "CASHFLOW_RESEARCH_DISCLAIMER",
    "MetricExplanation",
    "build_explanation",
]

CASHFLOW_RESEARCH_DISCLAIMER = (
    "Cash Flow Intelligence is a research analysis of reported cash flow "
    "statement figures. It is not investment advice, a buy/sell recommendation, "
    "or a forecast of future liquidity. Metrics are deterministic "
    "transformations of provided inputs; missing data reduces coverage and "
    "confidence. Always verify source filings."
)
