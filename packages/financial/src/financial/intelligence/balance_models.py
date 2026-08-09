"""Immutable output models for Balance Sheet Intelligence (F2.3)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from financial.intelligence.income_explainability import MetricExplanation
from financial.intelligence.income_models import TrendDirection
from financial.validation import ValidationResult

__all__ = [
    "BalanceQualityFlag",
    "LiquidityMetrics",
    "LeverageMetrics",
    "AssetMetrics",
    "LiabilityMetrics",
    "EquityMetrics",
    "WorkingCapitalMetrics",
    "BalanceTrendSummary",
    "BalanceAnalysisMetadata",
    "BalanceSheetAnalysis",
]


class BalanceQualityFlag(str, Enum):
    """Standardized balance-sheet quality / risk flags (research only)."""

    STRONG_LIQUIDITY = "strong_liquidity"
    WEAK_LIQUIDITY = "weak_liquidity"
    EXCESSIVE_LEVERAGE = "excessive_leverage"
    CONSERVATIVE_CAPITAL_STRUCTURE = "conservative_capital_structure"
    HIGH_GOODWILL = "high_goodwill"
    HIGH_INTANGIBLE_ASSETS = "high_intangible_assets"
    WORKING_CAPITAL_PRESSURE = "working_capital_pressure"
    STRONG_EQUITY_BASE = "strong_equity_base"
    WEAK_EQUITY_BASE = "weak_equity_base"
    HEALTHY_BALANCE_SHEET = "healthy_balance_sheet"
    BALANCE_SHEET_WARNING = "balance_sheet_warning"


@dataclass(frozen=True, slots=True)
class LiquidityMetrics:
    """Liquidity ratios and working-capital levels."""

    current_ratio: float | None = None
    quick_ratio: float | None = None
    cash_ratio: float | None = None
    working_capital: float | None = None
    net_working_capital: float | None = None
    working_capital_trend: TrendDirection | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_ratio": self.current_ratio,
            "quick_ratio": self.quick_ratio,
            "cash_ratio": self.cash_ratio,
            "working_capital": self.working_capital,
            "net_working_capital": self.net_working_capital,
            "working_capital_trend": (
                self.working_capital_trend.value
                if self.working_capital_trend
                else None
            ),
        }


@dataclass(frozen=True, slots=True)
class LeverageMetrics:
    """Leverage and capital-structure metrics."""

    debt_to_equity: float | None = None
    debt_to_assets: float | None = None
    equity_ratio: float | None = None
    net_debt: float | None = None
    net_debt_to_equity: float | None = None
    capital_structure_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "debt_to_equity": self.debt_to_equity,
            "debt_to_assets": self.debt_to_assets,
            "equity_ratio": self.equity_ratio,
            "net_debt": self.net_debt,
            "net_debt_to_equity": self.net_debt_to_equity,
            "capital_structure_summary": self.capital_structure_summary,
        }


@dataclass(frozen=True, slots=True)
class AssetMetrics:
    """Asset composition and quality indicators (fractions of total assets)."""

    current_asset_composition: float | None = None
    non_current_asset_composition: float | None = None
    cash_concentration: float | None = None
    inventory_concentration: float | None = None
    receivable_concentration: float | None = None
    goodwill_pct: float | None = None
    intangible_asset_pct: float | None = None
    asset_quality_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_asset_composition": self.current_asset_composition,
            "non_current_asset_composition": self.non_current_asset_composition,
            "cash_concentration": self.cash_concentration,
            "inventory_concentration": self.inventory_concentration,
            "receivable_concentration": self.receivable_concentration,
            "goodwill_pct": self.goodwill_pct,
            "intangible_asset_pct": self.intangible_asset_pct,
            "asset_quality_score": self.asset_quality_score,
        }


@dataclass(frozen=True, slots=True)
class LiabilityMetrics:
    """Liability mix and exposure metrics."""

    current_liability_mix: float | None = None
    long_term_liability_mix: float | None = None
    debt_structure: float | None = None
    lease_liability_exposure: float | None = None
    deferred_tax_exposure: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_liability_mix": self.current_liability_mix,
            "long_term_liability_mix": self.long_term_liability_mix,
            "debt_structure": self.debt_structure,
            "lease_liability_exposure": self.lease_liability_exposure,
            "deferred_tax_exposure": self.deferred_tax_exposure,
        }


@dataclass(frozen=True, slots=True)
class EquityMetrics:
    """Equity / book-value metrics."""

    book_value: float | None = None
    tangible_book_value: float | None = None
    retained_earnings_ratio: float | None = None
    treasury_share_impact: float | None = None
    equity_growth: float | None = None
    capital_quality: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "book_value": self.book_value,
            "tangible_book_value": self.tangible_book_value,
            "retained_earnings_ratio": self.retained_earnings_ratio,
            "treasury_share_impact": self.treasury_share_impact,
            "equity_growth": self.equity_growth,
            "capital_quality": self.capital_quality,
        }


@dataclass(frozen=True, slots=True)
class WorkingCapitalMetrics:
    """Working-capital / short-term solvency indicators."""

    cash_position: float | None = None
    inventory_efficiency: float | None = None
    receivable_dependence: float | None = None
    liquidity_buffer: float | None = None
    short_term_solvency: float | None = None
    balance_sheet_strength: float | None = None
    liquidity_quality: float | None = None
    capital_quality: float | None = None
    asset_quality: float | None = None
    debt_burden: float | None = None
    financial_flexibility: float | None = None
    # Operating WC = AR + Inventory − AP (cash/debt excluded; all three required)
    operating_working_capital: float | None = None
    operating_working_capital_change: float | None = None
    operating_working_capital_change_rate: float | None = None
    # Component growth (adjacent annual periods when available)
    receivables_growth: float | None = None
    inventory_growth: float | None = None
    payables_growth: float | None = None
    # Growth gaps vs revenue / COGS (evidence only — no invented warning thresholds)
    receivables_vs_revenue_growth: float | None = None
    inventory_vs_revenue_growth: float | None = None
    payables_vs_cogs_growth: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cash_position": self.cash_position,
            "inventory_efficiency": self.inventory_efficiency,
            "receivable_dependence": self.receivable_dependence,
            "liquidity_buffer": self.liquidity_buffer,
            "short_term_solvency": self.short_term_solvency,
            "balance_sheet_strength": self.balance_sheet_strength,
            "liquidity_quality": self.liquidity_quality,
            "capital_quality": self.capital_quality,
            "asset_quality": self.asset_quality,
            "debt_burden": self.debt_burden,
            "financial_flexibility": self.financial_flexibility,
            "operating_working_capital": self.operating_working_capital,
            "operating_working_capital_change": self.operating_working_capital_change,
            "operating_working_capital_change_rate": (
                self.operating_working_capital_change_rate
            ),
            "receivables_growth": self.receivables_growth,
            "inventory_growth": self.inventory_growth,
            "payables_growth": self.payables_growth,
            "receivables_vs_revenue_growth": self.receivables_vs_revenue_growth,
            "inventory_vs_revenue_growth": self.inventory_vs_revenue_growth,
            "payables_vs_cogs_growth": self.payables_vs_cogs_growth,
        }


@dataclass(frozen=True, slots=True)
class BalanceTrendSummary:
    """Per-dimension trend classifications."""

    liquidity: TrendDirection = TrendDirection.STABLE
    leverage: TrendDirection = TrendDirection.STABLE
    asset_quality: TrendDirection = TrendDirection.STABLE
    capital_structure: TrendDirection = TrendDirection.STABLE
    working_capital: TrendDirection = TrendDirection.STABLE

    def to_dict(self) -> dict[str, Any]:
        return {
            "liquidity": self.liquidity.value,
            "leverage": self.leverage.value,
            "asset_quality": self.asset_quality.value,
            "capital_structure": self.capital_structure.value,
            "working_capital": self.working_capital.value,
        }


@dataclass(frozen=True, slots=True)
class BalanceAnalysisMetadata:
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
class BalanceSheetAnalysis:
    """Full Balance Sheet Intelligence result (research artifact)."""

    liquidity: LiquidityMetrics
    leverage: LeverageMetrics
    assets: AssetMetrics
    liabilities: LiabilityMetrics
    equity: EquityMetrics
    working_capital: WorkingCapitalMetrics
    quality_flags: tuple[BalanceQualityFlag, ...]
    trend_summary: BalanceTrendSummary
    validation: ValidationResult
    explainability: tuple[MetricExplanation, ...]
    metadata: BalanceAnalysisMetadata
    research_disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "liquidity": self.liquidity.to_dict(),
            "leverage": self.leverage.to_dict(),
            "assets": self.assets.to_dict(),
            "liabilities": self.liabilities.to_dict(),
            "equity": self.equity.to_dict(),
            "working_capital": self.working_capital.to_dict(),
            "quality_flags": [f.value for f in self.quality_flags],
            "trend_summary": self.trend_summary.to_dict(),
            "validation": self.validation.to_dict(),
            "explainability": [e.to_dict() for e in self.explainability],
            "metadata": self.metadata.to_dict(),
            "research_disclaimer": self.research_disclaimer,
        }
