"""Explainability for Balance Sheet Intelligence (F2.3).

Reuses shared MetricExplanation / build_explanation from income explainability.
"""

from __future__ import annotations

from financial.intelligence.income_explainability import (
    MetricExplanation,
    build_explanation,
)

__all__ = [
    "BALANCE_RESEARCH_DISCLAIMER",
    "MetricExplanation",
    "build_explanation",
]

BALANCE_RESEARCH_DISCLAIMER = (
    "Balance Sheet Intelligence is a research analysis of reported "
    "financial position figures. It is not investment advice, a buy/sell "
    "recommendation, or a forecast of future solvency. Metrics are "
    "deterministic transformations of provided inputs; missing data reduces "
    "coverage and confidence. Always verify source filings."
)
