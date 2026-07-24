"""Immutable output models for Income Statement Intelligence (F2.2)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from financial.intelligence.income_explainability import MetricExplanation
from financial.validation import ValidationResult

__all__ = [
    "TrendDirection",
    "RevenueTrendClass",
    "QualityFlag",
    "RevenueMetrics",
    "MarginMetrics",
    "ExpenseMetrics",
    "ProfitabilityMetrics",
    "GrowthMetrics",
    "ConsistencyMetrics",
    "IncomeAnalysisMetadata",
    "IncomeStatementAnalysis",
]


class TrendDirection(str, Enum):
    """Aggregate trend classification for research display."""

    IMPROVING = "improving"
    STABLE = "stable"
    WEAKENING = "weakening"


class RevenueTrendClass(str, Enum):
    """Revenue path classification."""

    ACCELERATING = "accelerating"
    STEADY_GROWTH = "steady_growth"
    DECELERATING = "decelerating"
    FLAT = "flat"
    DECLINING = "declining"
    VOLATILE = "volatile"
    INSUFFICIENT_HISTORY = "insufficient_history"


class QualityFlag(str, Enum):
    """Standardized income-statement quality / risk flags (research only)."""

    HEALTHY_GROWTH = "healthy_growth"
    DECLINING_REVENUE = "declining_revenue"
    MARGIN_EXPANSION = "margin_expansion"
    MARGIN_COMPRESSION = "margin_compression"
    HIGH_OPERATING_LEVERAGE = "high_operating_leverage"
    WEAK_EARNINGS_QUALITY = "weak_earnings_quality"
    STRONG_EARNINGS_QUALITY = "strong_earnings_quality"
    HIGH_TAX_BURDEN = "high_tax_burden"
    HIGH_INTEREST_BURDEN = "high_interest_burden"


@dataclass(frozen=True, slots=True)
class RevenueMetrics:
    """Revenue level and growth statistics."""

    revenue: float | None = None
    revenue_growth: float | None = None
    qoq_growth: float | None = None
    yoy_growth: float | None = None
    cagr: float | None = None
    growth_stability: float | None = None
    trend_class: RevenueTrendClass = RevenueTrendClass.INSUFFICIENT_HISTORY

    def to_dict(self) -> dict[str, Any]:
        return {
            "revenue": self.revenue,
            "revenue_growth": self.revenue_growth,
            "qoq_growth": self.qoq_growth,
            "yoy_growth": self.yoy_growth,
            "cagr": self.cagr,
            "growth_stability": self.growth_stability,
            "trend_class": self.trend_class.value,
        }


@dataclass(frozen=True, slots=True)
class MarginMetrics:
    """Profitability margins as fractions of revenue (e.g. 0.25 = 25%)."""

    gross_margin: float | None = None
    ebitda_margin: float | None = None
    ebit_margin: float | None = None
    operating_margin: float | None = None
    pretax_margin: float | None = None
    net_margin: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "gross_margin": self.gross_margin,
            "ebitda_margin": self.ebitda_margin,
            "ebit_margin": self.ebit_margin,
            "operating_margin": self.operating_margin,
            "pretax_margin": self.pretax_margin,
            "net_margin": self.net_margin,
        }


@dataclass(frozen=True, slots=True)
class ExpenseMetrics:
    """Expense ratios as fractions of revenue."""

    cogs_pct: float | None = None
    rd_pct: float | None = None
    sga_pct: float | None = None
    operating_expense_pct: float | None = None
    interest_pct: float | None = None
    tax_pct: float | None = None
    other_income_pct: float | None = None
    expense_trend: TrendDirection | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cogs_pct": self.cogs_pct,
            "rd_pct": self.rd_pct,
            "sga_pct": self.sga_pct,
            "operating_expense_pct": self.operating_expense_pct,
            "interest_pct": self.interest_pct,
            "tax_pct": self.tax_pct,
            "other_income_pct": self.other_income_pct,
            "expense_trend": (
                self.expense_trend.value if self.expense_trend else None
            ),
        }


@dataclass(frozen=True, slots=True)
class ProfitabilityMetrics:
    """Profit quality and margin-change signals."""

    gross_profit_quality: float | None = None
    operating_profit_quality: float | None = None
    net_income_quality: float | None = None
    margin_stability: float | None = None
    margin_expansion: float | None = None
    margin_compression: float | None = None
    eps: float | None = None
    diluted_eps: float | None = None
    eps_growth: float | None = None
    eps_stability: float | None = None
    earnings_consistency: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "gross_profit_quality": self.gross_profit_quality,
            "operating_profit_quality": self.operating_profit_quality,
            "net_income_quality": self.net_income_quality,
            "margin_stability": self.margin_stability,
            "margin_expansion": self.margin_expansion,
            "margin_compression": self.margin_compression,
            "eps": self.eps,
            "diluted_eps": self.diluted_eps,
            "eps_growth": self.eps_growth,
            "eps_stability": self.eps_stability,
            "earnings_consistency": self.earnings_consistency,
        }


@dataclass(frozen=True, slots=True)
class GrowthMetrics:
    """Cross-cutting growth summary."""

    revenue_growth: float | None = None
    ebit_growth: float | None = None
    net_income_growth: float | None = None
    eps_growth: float | None = None
    operating_leverage: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "revenue_growth": self.revenue_growth,
            "ebit_growth": self.ebit_growth,
            "net_income_growth": self.net_income_growth,
            "eps_growth": self.eps_growth,
            "operating_leverage": self.operating_leverage,
        }


@dataclass(frozen=True, slots=True)
class ConsistencyMetrics:
    """Stability / burden / dependence scores in [0, 1] where applicable."""

    revenue_consistency: float | None = None
    margin_consistency: float | None = None
    earnings_stability: float | None = None
    operating_leverage: float | None = None
    interest_burden: float | None = None
    tax_burden: float | None = None
    other_income_dependence: float | None = None
    recurring_earnings: float | None = None
    one_time_items_detected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "revenue_consistency": self.revenue_consistency,
            "margin_consistency": self.margin_consistency,
            "earnings_stability": self.earnings_stability,
            "operating_leverage": self.operating_leverage,
            "interest_burden": self.interest_burden,
            "tax_burden": self.tax_burden,
            "other_income_dependence": self.other_income_dependence,
            "recurring_earnings": self.recurring_earnings,
            "one_time_items_detected": self.one_time_items_detected,
        }


@dataclass(frozen=True, slots=True)
class IncomeAnalysisMetadata:
    """Analysis provenance metadata."""

    engine_version: str
    periods_used: int
    primary_period_end: str | None = None
    company: str = ""
    ticker: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_version": self.engine_version,
            "periods_used": self.periods_used,
            "primary_period_end": self.primary_period_end,
            "company": self.company,
            "ticker": self.ticker,
        }


@dataclass(frozen=True, slots=True)
class IncomeStatementAnalysis:
    """Full Income Statement Intelligence result (research artifact)."""

    revenue: RevenueMetrics
    margins: MarginMetrics
    expenses: ExpenseMetrics
    profitability: ProfitabilityMetrics
    growth: GrowthMetrics
    consistency: ConsistencyMetrics
    quality_flags: tuple[QualityFlag, ...]
    trend_summary: TrendDirection
    validation: ValidationResult
    explainability: tuple[MetricExplanation, ...]
    metadata: IncomeAnalysisMetadata
    research_disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "revenue": self.revenue.to_dict(),
            "margins": self.margins.to_dict(),
            "expenses": self.expenses.to_dict(),
            "profitability": self.profitability.to_dict(),
            "growth": self.growth.to_dict(),
            "consistency": self.consistency.to_dict(),
            "quality_flags": [f.value for f in self.quality_flags],
            "trend_summary": self.trend_summary.value,
            "validation": self.validation.to_dict(),
            "explainability": [e.to_dict() for e in self.explainability],
            "metadata": self.metadata.to_dict(),
            "research_disclaimer": self.research_disclaimer,
        }
