"""Immutable output models for Financial Statement Aggregator (F2.7)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from financial.intelligence.balance_models import BalanceSheetAnalysis
from financial.intelligence.cashflow_models import CashFlowAnalysis
from financial.intelligence.income_explainability import MetricExplanation
from financial.intelligence.income_models import IncomeStatementAnalysis
from financial.intelligence.ratio_models import FinancialRatioAnalysis
from financial.intelligence.trend_models import TrendAnalysis
from financial.validation import ValidationResult

__all__ = [
    "AggregatedQualityFlag",
    "OverallFinancialSummary",
    "FinancialAnalysisMetadata",
    "FinancialAnalysis",
]


class AggregatedQualityFlag(str, Enum):
    """Cross-module quality / risk summaries derived from module flags only."""

    EXCELLENT_FINANCIAL_HEALTH = "excellent_financial_health"
    HEALTHY_FINANCIAL_POSITION = "healthy_financial_position"
    NEEDS_ATTENTION = "needs_attention"
    LIQUIDITY_CONCERN = "liquidity_concern"
    LEVERAGE_CONCERN = "leverage_concern"
    CASH_FLOW_CONCERN = "cash_flow_concern"
    CONSISTENT_COMPOUNDER = "consistent_compounder"
    IMPROVING_FUNDAMENTALS = "improving_fundamentals"
    FINANCIAL_DETERIORATION = "financial_deterioration"


@dataclass(frozen=True, slots=True)
class OverallFinancialSummary:
    """Deterministic narrative summary composed from module outputs."""

    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    key_observations: tuple[str, ...] = ()
    data_completeness: str = "unknown"
    confidence_summary: str = "insufficient"
    health_label: str = "needs_attention"

    def to_dict(self) -> dict[str, Any]:
        return {
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "key_observations": list(self.key_observations),
            "data_completeness": self.data_completeness,
            "confidence_summary": self.confidence_summary,
            "health_label": self.health_label,
        }


@dataclass(frozen=True, slots=True)
class FinancialAnalysisMetadata:
    """Aggregator provenance metadata."""

    engine_version: str
    periods_used: int
    period_ends: tuple[str, ...]
    company: str = ""
    ticker: str = ""
    modules_composed: tuple[str, ...] = (
        "income_statement_intelligence",
        "balance_sheet_intelligence",
        "cash_flow_intelligence",
        "financial_ratio_engine",
        "trend_time_series_intelligence",
    )
    trend_included: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_version": self.engine_version,
            "periods_used": self.periods_used,
            "period_ends": list(self.period_ends),
            "company": self.company,
            "ticker": self.ticker,
            "modules_composed": list(self.modules_composed),
            "trend_included": self.trend_included,
        }


@dataclass(frozen=True, slots=True)
class FinancialAnalysis:
    """Unified Financial Statement Intelligence result (F2.7)."""

    metadata: FinancialAnalysisMetadata
    validation: ValidationResult
    income: IncomeStatementAnalysis
    balance_sheet: BalanceSheetAnalysis
    cash_flow: CashFlowAnalysis
    ratios: FinancialRatioAnalysis
    trends: TrendAnalysis | None
    overall_summary: OverallFinancialSummary
    quality_flags: tuple[AggregatedQualityFlag, ...]
    explainability: tuple[MetricExplanation, ...]
    research_disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "validation": self.validation.to_dict(),
            "income": self.income.to_dict(),
            "balance_sheet": self.balance_sheet.to_dict(),
            "cash_flow": self.cash_flow.to_dict(),
            "ratios": self.ratios.to_dict(),
            "trends": self.trends.to_dict() if self.trends is not None else None,
            "overall_summary": self.overall_summary.to_dict(),
            "quality_flags": [f.value for f in self.quality_flags],
            "explainability": [e.to_dict() for e in self.explainability],
            "research_disclaimer": self.research_disclaimer,
        }
