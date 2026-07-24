"""Immutable output models for Cash Flow Intelligence (F2.4)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from financial.intelligence.income_explainability import MetricExplanation
from financial.intelligence.income_models import TrendDirection
from financial.validation import ValidationResult

__all__ = [
    "CashFlowQualityFlag",
    "GrowthInvestmentClass",
    "OperatingCashMetrics",
    "InvestingCashMetrics",
    "FinancingCashMetrics",
    "FreeCashFlowMetrics",
    "CashQualityMetrics",
    "CashFlowTrendSummary",
    "CashFlowAnalysisMetadata",
    "CashFlowAnalysis",
]


class CashFlowQualityFlag(str, Enum):
    """Standardized cash-flow quality / risk flags (research only)."""

    STRONG_CASH_GENERATION = "strong_cash_generation"
    WEAK_CASH_GENERATION = "weak_cash_generation"
    NEGATIVE_FREE_CASH_FLOW = "negative_free_cash_flow"
    HEAVY_CAPEX = "heavy_capex"
    AGGRESSIVE_DEBT_FUNDING = "aggressive_debt_funding"
    HEALTHY_CAPITAL_ALLOCATION = "healthy_capital_allocation"
    SHAREHOLDER_FRIENDLY = "shareholder_friendly"
    CASH_FLOW_WARNING = "cash_flow_warning"
    EXCELLENT_CASH_QUALITY = "excellent_cash_quality"


class GrowthInvestmentClass(str, Enum):
    """Capex / investment activity classification."""

    MAINTENANCE = "maintenance"
    GROWTH = "growth"
    AGGRESSIVE_GROWTH = "aggressive_growth"
    NET_DIVESTING = "net_divesting"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True, slots=True)
class OperatingCashMetrics:
    """Operating cash flow intelligence."""

    operating_cash_flow: float | None = None
    operating_cash_flow_growth: float | None = None
    cash_earnings_quality: float | None = None
    cash_conversion: float | None = None
    cash_flow_stability: float | None = None
    cash_generation_trend: TrendDirection | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "operating_cash_flow": self.operating_cash_flow,
            "operating_cash_flow_growth": self.operating_cash_flow_growth,
            "cash_earnings_quality": self.cash_earnings_quality,
            "cash_conversion": self.cash_conversion,
            "cash_flow_stability": self.cash_flow_stability,
            "cash_generation_trend": (
                self.cash_generation_trend.value
                if self.cash_generation_trend
                else None
            ),
        }


@dataclass(frozen=True, slots=True)
class InvestingCashMetrics:
    """Investing cash flow intelligence."""

    capex: float | None = None
    capex_intensity: float | None = None
    acquisitions: float | None = None
    investment_activity: float | None = None
    asset_sales: float | None = None
    investment_discipline: float | None = None
    growth_investment_class: GrowthInvestmentClass = (
        GrowthInvestmentClass.INSUFFICIENT_DATA
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "capex": self.capex,
            "capex_intensity": self.capex_intensity,
            "acquisitions": self.acquisitions,
            "investment_activity": self.investment_activity,
            "asset_sales": self.asset_sales,
            "investment_discipline": self.investment_discipline,
            "growth_investment_class": self.growth_investment_class.value,
        }


@dataclass(frozen=True, slots=True)
class FinancingCashMetrics:
    """Financing cash flow intelligence."""

    debt_issued: float | None = None
    debt_repaid: float | None = None
    dividends_paid: float | None = None
    share_buybacks: float | None = None
    share_issuance: float | None = None
    financing_dependence: float | None = None
    capital_allocation_quality: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "debt_issued": self.debt_issued,
            "debt_repaid": self.debt_repaid,
            "dividends_paid": self.dividends_paid,
            "share_buybacks": self.share_buybacks,
            "share_issuance": self.share_issuance,
            "financing_dependence": self.financing_dependence,
            "capital_allocation_quality": self.capital_allocation_quality,
        }


@dataclass(frozen=True, slots=True)
class FreeCashFlowMetrics:
    """Free cash flow and owner-earnings metrics."""

    free_cash_flow: float | None = None
    fcf_growth: float | None = None
    fcf_margin: float | None = None
    fcf_stability: float | None = None
    owner_earnings: float | None = None
    cash_surplus: float | None = None
    fcf_source: str = "unavailable"

    def to_dict(self) -> dict[str, Any]:
        return {
            "free_cash_flow": self.free_cash_flow,
            "fcf_growth": self.fcf_growth,
            "fcf_margin": self.fcf_margin,
            "fcf_stability": self.fcf_stability,
            "owner_earnings": self.owner_earnings,
            "cash_surplus": self.cash_surplus,
            "fcf_source": self.fcf_source,
        }


@dataclass(frozen=True, slots=True)
class CashQualityMetrics:
    """Cross-cutting cash quality / sustainability scores in [0, 1]."""

    operating_cash_quality: float | None = None
    investment_discipline: float | None = None
    financing_quality: float | None = None
    cash_sustainability: float | None = None
    dividend_sustainability: float | None = None
    buyback_sustainability: float | None = None
    debt_sustainability: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "operating_cash_quality": self.operating_cash_quality,
            "investment_discipline": self.investment_discipline,
            "financing_quality": self.financing_quality,
            "cash_sustainability": self.cash_sustainability,
            "dividend_sustainability": self.dividend_sustainability,
            "buyback_sustainability": self.buyback_sustainability,
            "debt_sustainability": self.debt_sustainability,
        }


@dataclass(frozen=True, slots=True)
class CashFlowTrendSummary:
    """Per-dimension trend classifications."""

    operating_cash_flow: TrendDirection = TrendDirection.STABLE
    free_cash_flow: TrendDirection = TrendDirection.STABLE
    capital_allocation: TrendDirection = TrendDirection.STABLE
    debt_activity: TrendDirection = TrendDirection.STABLE

    def to_dict(self) -> dict[str, Any]:
        return {
            "operating_cash_flow": self.operating_cash_flow.value,
            "free_cash_flow": self.free_cash_flow.value,
            "capital_allocation": self.capital_allocation.value,
            "debt_activity": self.debt_activity.value,
        }


@dataclass(frozen=True, slots=True)
class CashFlowAnalysisMetadata:
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
class CashFlowAnalysis:
    """Full Cash Flow Intelligence result (research artifact)."""

    operating: OperatingCashMetrics
    investing: InvestingCashMetrics
    financing: FinancingCashMetrics
    free_cash_flow: FreeCashFlowMetrics
    quality: CashQualityMetrics
    quality_flags: tuple[CashFlowQualityFlag, ...]
    trend_summary: CashFlowTrendSummary
    validation: ValidationResult
    explainability: tuple[MetricExplanation, ...]
    metadata: CashFlowAnalysisMetadata
    research_disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "operating": self.operating.to_dict(),
            "investing": self.investing.to_dict(),
            "financing": self.financing.to_dict(),
            "free_cash_flow": self.free_cash_flow.to_dict(),
            "quality": self.quality.to_dict(),
            "quality_flags": [f.value for f in self.quality_flags],
            "trend_summary": self.trend_summary.to_dict(),
            "validation": self.validation.to_dict(),
            "explainability": [e.to_dict() for e in self.explainability],
            "metadata": self.metadata.to_dict(),
            "research_disclaimer": self.research_disclaimer,
        }
