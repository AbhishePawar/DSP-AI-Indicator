"""Explainability for Financial Statement Aggregator (F2.7)."""

from __future__ import annotations

from financial.intelligence.income_explainability import (
    MetricExplanation,
    build_explanation,
)

__all__ = [
    "AGGREGATOR_RESEARCH_DISCLAIMER",
    "MetricExplanation",
    "build_explanation",
]

AGGREGATOR_RESEARCH_DISCLAIMER = (
    "Financial Statement Aggregator composes Income, Balance Sheet, Cash Flow, "
    "Ratio, and Trend intelligence into one research view. It does not compute "
    "new financial ratios or forecasts. It is not investment advice or a "
    "buy/sell recommendation. Always verify source filings and underlying "
    "module explainability records."
)
