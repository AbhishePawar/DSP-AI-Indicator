"""Explainability for Financial Ratio Engine (F2.5)."""

from __future__ import annotations

from financial.intelligence.income_explainability import (
    MetricExplanation,
    build_explanation,
)

__all__ = [
    "RATIO_RESEARCH_DISCLAIMER",
    "MetricExplanation",
    "build_explanation",
]

RATIO_RESEARCH_DISCLAIMER = (
    "Financial Ratio Engine is a research analysis of reported financial "
    "statements. It is not investment advice, a buy/sell recommendation, or a "
    "forecast. Ratios are deterministic transformations of provided inputs; "
    "missing data reduces coverage and confidence. Always verify source filings."
)
