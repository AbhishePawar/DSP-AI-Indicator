"""Explainability for Trend & Time-Series Intelligence (F2.6)."""

from __future__ import annotations

from financial.intelligence.income_explainability import (
    MetricExplanation,
    build_explanation,
)

__all__ = [
    "TREND_RESEARCH_DISCLAIMER",
    "MetricExplanation",
    "build_explanation",
]

TREND_RESEARCH_DISCLAIMER = (
    "Trend & Time-Series Intelligence is a research analysis of historical "
    "financial-statement intelligence outputs. It is not investment advice, "
    "a buy/sell recommendation, or a forecast of future results. Trends are "
    "deterministic transformations of prior-period analyses; missing data "
    "reduces coverage and confidence. Always verify source filings."
)
