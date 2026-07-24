"""Immutable output models for Financial Ratio Engine (F2.5)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from financial.intelligence.income_explainability import MetricExplanation
from financial.intelligence.income_models import TrendDirection
from financial.validation import ValidationResult

__all__ = [
    "BenchmarkClass",
    "RatioQualityFlag",
    "RatioMetric",
    "CapitalAllocationMetrics",
    "RatioTrendSummary",
    "RatioAnalysisMetadata",
    "FinancialRatioAnalysis",
]


class BenchmarkClass(str, Enum):
    """Research benchmark buckets (not investment grades)."""

    EXCELLENT = "excellent"
    STRONG = "strong"
    ADEQUATE = "adequate"
    WEAK = "weak"
    POOR = "poor"
    INSUFFICIENT = "insufficient"


class RatioQualityFlag(str, Enum):
    """Standardized cross-statement ratio quality flags."""

    EXCELLENT_PROFITABILITY = "excellent_profitability"
    WEAK_PROFITABILITY = "weak_profitability"
    STRONG_LIQUIDITY = "strong_liquidity"
    WEAK_LIQUIDITY = "weak_liquidity"
    HIGH_LEVERAGE = "high_leverage"
    LOW_LEVERAGE = "low_leverage"
    EFFICIENT_OPERATIONS = "efficient_operations"
    POOR_EFFICIENCY = "poor_efficiency"
    STRONG_CASH_GENERATION = "strong_cash_generation"
    WEAK_CASH_GENERATION = "weak_cash_generation"
    SHAREHOLDER_FRIENDLY = "shareholder_friendly"
    CAPITAL_ALLOCATION_WARNING = "capital_allocation_warning"


@dataclass(frozen=True, slots=True)
class RatioMetric:
    """One ratio with scoring + explainability fields."""

    name: str
    value: float | None
    formula: str
    inputs: Mapping[str, Any]
    intermediates: Mapping[str, Any]
    benchmark: BenchmarkClass
    trend: TrendDirection | None
    confidence: str
    interpretation: str
    risk_notes: str = ""
    limitations: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "formula": self.formula,
            "inputs": dict(self.inputs),
            "intermediates": dict(self.intermediates),
            "benchmark": self.benchmark.value,
            "trend": self.trend.value if self.trend else None,
            "confidence": self.confidence,
            "interpretation": self.interpretation,
            "risk_notes": self.risk_notes,
            "limitations": self.limitations,
        }


@dataclass(frozen=True, slots=True)
class CapitalAllocationMetrics:
    """Capital allocation research scores."""

    capex_discipline: float | None = None
    dividend_sustainability: float | None = None
    buyback_sustainability: float | None = None
    debt_reduction_quality: float | None = None
    capital_allocation_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "capex_discipline": self.capex_discipline,
            "dividend_sustainability": self.dividend_sustainability,
            "buyback_sustainability": self.buyback_sustainability,
            "debt_reduction_quality": self.debt_reduction_quality,
            "capital_allocation_score": self.capital_allocation_score,
        }


@dataclass(frozen=True, slots=True)
class RatioTrendSummary:
    """Aggregate trend across ratio families."""

    profitability: TrendDirection = TrendDirection.STABLE
    liquidity: TrendDirection = TrendDirection.STABLE
    leverage: TrendDirection = TrendDirection.STABLE
    efficiency: TrendDirection = TrendDirection.STABLE
    cash_flow: TrendDirection = TrendDirection.STABLE

    def to_dict(self) -> dict[str, Any]:
        return {
            "profitability": self.profitability.value,
            "liquidity": self.liquidity.value,
            "leverage": self.leverage.value,
            "efficiency": self.efficiency.value,
            "cash_flow": self.cash_flow.value,
        }


@dataclass(frozen=True, slots=True)
class RatioAnalysisMetadata:
    """Analysis provenance metadata."""

    engine_version: str
    periods_used: int
    primary_period_end: str | None = None
    company: str = ""
    ticker: str = ""
    composed_from: tuple[str, ...] = (
        "income_statement_intelligence",
        "balance_sheet_intelligence",
        "cash_flow_intelligence",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_version": self.engine_version,
            "periods_used": self.periods_used,
            "primary_period_end": self.primary_period_end,
            "company": self.company,
            "ticker": self.ticker,
            "composed_from": list(self.composed_from),
        }


@dataclass(frozen=True, slots=True)
class FinancialRatioAnalysis:
    """Full Financial Ratio Engine result (research artifact)."""

    profitability: tuple[RatioMetric, ...]
    liquidity: tuple[RatioMetric, ...]
    leverage: tuple[RatioMetric, ...]
    efficiency: tuple[RatioMetric, ...]
    cash_flow: tuple[RatioMetric, ...]
    shareholder: tuple[RatioMetric, ...]
    capital_allocation: CapitalAllocationMetrics
    quality_flags: tuple[RatioQualityFlag, ...]
    trend_summary: RatioTrendSummary
    validation: ValidationResult
    explainability: tuple[MetricExplanation, ...]
    metadata: RatioAnalysisMetadata
    research_disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "profitability": [r.to_dict() for r in self.profitability],
            "liquidity": [r.to_dict() for r in self.liquidity],
            "leverage": [r.to_dict() for r in self.leverage],
            "efficiency": [r.to_dict() for r in self.efficiency],
            "cash_flow": [r.to_dict() for r in self.cash_flow],
            "shareholder": [r.to_dict() for r in self.shareholder],
            "capital_allocation": self.capital_allocation.to_dict(),
            "quality_flags": [f.value for f in self.quality_flags],
            "trend_summary": self.trend_summary.to_dict(),
            "validation": self.validation.to_dict(),
            "explainability": [e.to_dict() for e in self.explainability],
            "metadata": self.metadata.to_dict(),
            "research_disclaimer": self.research_disclaimer,
        }
