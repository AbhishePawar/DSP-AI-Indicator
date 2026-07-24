"""Reusable research quality flags for valuation engines."""

from __future__ import annotations

from enum import Enum

__all__ = ["QualityFlag"]


class QualityFlag(str, Enum):
    """Research quality / risk flags (not trade recommendations)."""

    HIGH_ROE = "high_roe"
    DECLINING_ROE = "declining_roe"
    NEGATIVE_RESIDUAL_INCOME = "negative_residual_income"
    HIGH_DEBT = "high_debt"
    WEAK_CASH_FLOW = "weak_cash_flow"
    WEAK_BOOK_VALUE_GROWTH = "weak_book_value_growth"
    ACCOUNTING_WARNING = "accounting_warning"
    CAPITAL_EFFICIENT = "capital_efficient"
    LOW_DATA_QUALITY = "low_data_quality"
    FORECAST_RISK = "forecast_risk"
    MARGIN_COMPRESSION = "margin_compression"
    TERMINAL_VALUE_DOMINANCE = "terminal_value_dominance"
    OVERLY_OPTIMISTIC_ASSUMPTIONS = "overly_optimistic_assumptions"
