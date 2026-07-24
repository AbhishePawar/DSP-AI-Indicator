"""Immutable output models for Trend & Time-Series Intelligence (F2.6)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from financial.intelligence.income_explainability import MetricExplanation
from financial.models import FinancialStatements
from financial.validation import ValidationResult

__all__ = [
    "TrendClass",
    "TrendQualityFlag",
    "FinancialStatementsHistory",
    "MetricTrend",
    "TrendConsistencyMetrics",
    "TrendSummary",
    "TrendAnalysisMetadata",
    "TrendAnalysis",
]


class TrendClass(str, Enum):
    """Direction / volatility classification for a metric series."""

    STRONGLY_IMPROVING = "strongly_improving"
    IMPROVING = "improving"
    STABLE = "stable"
    WEAKENING = "weakening"
    STRONGLY_WEAKENING = "strongly_weakening"
    HIGHLY_VOLATILE = "highly_volatile"
    INSUFFICIENT = "insufficient"


class TrendQualityFlag(str, Enum):
    """Standardized multi-period quality / risk flags."""

    CONSISTENT_COMPOUNDER = "consistent_compounder"
    IMPROVING_BUSINESS = "improving_business"
    DETERIORATING_BUSINESS = "deteriorating_business"
    MARGIN_EXPANSION = "margin_expansion"
    MARGIN_COMPRESSION = "margin_compression"
    CASH_FLOW_IMPROVING = "cash_flow_improving"
    DEBT_INCREASING = "debt_increasing"
    DEBT_REDUCING = "debt_reducing"
    HIGH_VOLATILITY = "high_volatility"
    STABLE_COMPOUND_GROWTH = "stable_compound_growth"


@dataclass(frozen=True, slots=True)
class FinancialStatementsHistory:
    """Ordered multi-period statement history (canonical trend input)."""

    statements: tuple[FinancialStatements, ...]

    def __len__(self) -> int:
        return len(self.statements)


@dataclass(frozen=True, slots=True)
class MetricTrend:
    """Trend summary for one reused intelligence metric series."""

    name: str
    values: tuple[float | None, ...]
    latest_growth: float | None
    cagr: float | None
    classification: TrendClass
    consistency: float | None
    acceleration: float | None
    confidence: str
    interpretation: str
    method: str
    intermediates: Mapping[str, Any]
    limitations: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "values": list(self.values),
            "latest_growth": self.latest_growth,
            "cagr": self.cagr,
            "classification": self.classification.value,
            "consistency": self.consistency,
            "acceleration": self.acceleration,
            "confidence": self.confidence,
            "interpretation": self.interpretation,
            "method": self.method,
            "intermediates": dict(self.intermediates),
            "limitations": self.limitations,
        }


@dataclass(frozen=True, slots=True)
class TrendConsistencyMetrics:
    """Cross-metric consistency / volatility research scores."""

    consistency_score: float | None = None
    volatility_score: float | None = None
    stability_score: float | None = None
    persistence_score: float | None = None
    financial_predictability: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "consistency_score": self.consistency_score,
            "volatility_score": self.volatility_score,
            "stability_score": self.stability_score,
            "persistence_score": self.persistence_score,
            "financial_predictability": self.financial_predictability,
        }


@dataclass(frozen=True, slots=True)
class TrendSummary:
    """Aggregate directional summary across families."""

    revenue: TrendClass = TrendClass.INSUFFICIENT
    profitability: TrendClass = TrendClass.INSUFFICIENT
    cash_flow: TrendClass = TrendClass.INSUFFICIENT
    balance_sheet: TrendClass = TrendClass.INSUFFICIENT
    ratios: TrendClass = TrendClass.INSUFFICIENT
    overall: TrendClass = TrendClass.INSUFFICIENT
    insights: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "revenue": self.revenue.value,
            "profitability": self.profitability.value,
            "cash_flow": self.cash_flow.value,
            "balance_sheet": self.balance_sheet.value,
            "ratios": self.ratios.value,
            "overall": self.overall.value,
            "insights": list(self.insights),
        }


@dataclass(frozen=True, slots=True)
class TrendAnalysisMetadata:
    """Analysis provenance metadata."""

    engine_version: str
    periods_used: int
    period_ends: tuple[str, ...]
    company: str = ""
    ticker: str = ""
    reused_engines: tuple[str, ...] = (
        "income_statement_intelligence",
        "balance_sheet_intelligence",
        "cash_flow_intelligence",
        "financial_ratio_engine",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_version": self.engine_version,
            "periods_used": self.periods_used,
            "period_ends": list(self.period_ends),
            "company": self.company,
            "ticker": self.ticker,
            "reused_engines": list(self.reused_engines),
        }


@dataclass(frozen=True, slots=True)
class TrendAnalysis:
    """Full Trend & Time-Series Intelligence result."""

    revenue_trends: tuple[MetricTrend, ...]
    profitability_trends: tuple[MetricTrend, ...]
    cash_flow_trends: tuple[MetricTrend, ...]
    balance_sheet_trends: tuple[MetricTrend, ...]
    ratio_trends: tuple[MetricTrend, ...]
    consistency: TrendConsistencyMetrics
    quality_flags: tuple[TrendQualityFlag, ...]
    trend_summary: TrendSummary
    validation: ValidationResult
    explainability: tuple[MetricExplanation, ...]
    metadata: TrendAnalysisMetadata
    research_disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "revenue_trends": [t.to_dict() for t in self.revenue_trends],
            "profitability_trends": [t.to_dict() for t in self.profitability_trends],
            "cash_flow_trends": [t.to_dict() for t in self.cash_flow_trends],
            "balance_sheet_trends": [t.to_dict() for t in self.balance_sheet_trends],
            "ratio_trends": [t.to_dict() for t in self.ratio_trends],
            "consistency": self.consistency.to_dict(),
            "quality_flags": [f.value for f in self.quality_flags],
            "trend_summary": self.trend_summary.to_dict(),
            "validation": self.validation.to_dict(),
            "explainability": [e.to_dict() for e in self.explainability],
            "metadata": self.metadata.to_dict(),
            "research_disclaimer": self.research_disclaimer,
        }
