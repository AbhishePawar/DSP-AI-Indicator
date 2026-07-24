"""Financial Statement Intelligence (F2.2–F2.7) — domain analysis only.

No forecasting, valuation, or provider integrations.
"""

from __future__ import annotations

from financial.intelligence.aggregator_engine import FinancialAggregatorEngine
from financial.intelligence.aggregator_explainability import (
    AGGREGATOR_RESEARCH_DISCLAIMER,
)
from financial.intelligence.aggregator_models import (
    AggregatedQualityFlag,
    FinancialAnalysis,
    FinancialAnalysisMetadata,
    OverallFinancialSummary,
)
from financial.intelligence.aggregator_validation import (
    FinancialAggregationError,
    validate_aggregation_inputs,
)
from financial.intelligence.balance_engine import BalanceSheetEngine
from financial.intelligence.balance_explainability import BALANCE_RESEARCH_DISCLAIMER
from financial.intelligence.balance_models import (
    AssetMetrics,
    BalanceAnalysisMetadata,
    BalanceQualityFlag,
    BalanceSheetAnalysis,
    BalanceTrendSummary,
    EquityMetrics,
    LeverageMetrics,
    LiabilityMetrics,
    LiquidityMetrics,
    WorkingCapitalMetrics,
)
from financial.intelligence.balance_validation import (
    BalanceAnalysisError,
    validate_balance_for_analysis,
)
from financial.intelligence.cashflow_engine import CashFlowEngine
from financial.intelligence.cashflow_explainability import CASHFLOW_RESEARCH_DISCLAIMER
from financial.intelligence.cashflow_models import (
    CashFlowAnalysis,
    CashFlowAnalysisMetadata,
    CashFlowQualityFlag,
    CashFlowTrendSummary,
    CashQualityMetrics,
    FinancingCashMetrics,
    FreeCashFlowMetrics,
    GrowthInvestmentClass,
    InvestingCashMetrics,
    OperatingCashMetrics,
)
from financial.intelligence.cashflow_validation import (
    CashFlowAnalysisError,
    validate_cashflow_for_analysis,
)
from financial.intelligence.income_engine import IncomeStatementEngine
from financial.intelligence.income_explainability import (
    RESEARCH_DISCLAIMER,
    MetricExplanation,
    build_explanation,
)
from financial.intelligence.income_models import (
    ConsistencyMetrics,
    ExpenseMetrics,
    GrowthMetrics,
    IncomeAnalysisMetadata,
    IncomeStatementAnalysis,
    MarginMetrics,
    ProfitabilityMetrics,
    QualityFlag,
    RevenueMetrics,
    RevenueTrendClass,
    TrendDirection,
)
from financial.intelligence.income_validation import (
    IncomeAnalysisError,
    validate_income_for_analysis,
)
from financial.intelligence.ratio_engine import FinancialRatioEngine
from financial.intelligence.ratio_explainability import RATIO_RESEARCH_DISCLAIMER
from financial.intelligence.ratio_models import (
    BenchmarkClass,
    CapitalAllocationMetrics,
    FinancialRatioAnalysis,
    RatioAnalysisMetadata,
    RatioMetric,
    RatioQualityFlag,
    RatioTrendSummary,
)
from financial.intelligence.ratio_validation import (
    FinancialRatioError,
    validate_ratio_inputs,
)
from financial.intelligence.trend_engine import TrendEngine
from financial.intelligence.trend_explainability import TREND_RESEARCH_DISCLAIMER
from financial.intelligence.trend_models import (
    FinancialStatementsHistory,
    MetricTrend,
    TrendAnalysis,
    TrendAnalysisMetadata,
    TrendClass,
    TrendConsistencyMetrics,
    TrendQualityFlag,
    TrendSummary,
)
from financial.intelligence.trend_validation import (
    TrendAnalysisError,
    validate_trend_history,
)

__all__ = [
    "AGGREGATOR_RESEARCH_DISCLAIMER",
    "BALANCE_RESEARCH_DISCLAIMER",
    "CASHFLOW_RESEARCH_DISCLAIMER",
    "RATIO_RESEARCH_DISCLAIMER",
    "TREND_RESEARCH_DISCLAIMER",
    "RESEARCH_DISCLAIMER",
    "AggregatedQualityFlag",
    "FinancialAggregationError",
    "FinancialAggregatorEngine",
    "FinancialAnalysis",
    "FinancialAnalysisMetadata",
    "OverallFinancialSummary",
    "validate_aggregation_inputs",
    "AssetMetrics",
    "BalanceAnalysisError",
    "BalanceAnalysisMetadata",
    "BalanceQualityFlag",
    "BalanceSheetAnalysis",
    "BalanceSheetEngine",
    "BalanceTrendSummary",
    "BenchmarkClass",
    "CapitalAllocationMetrics",
    "CashFlowAnalysis",
    "CashFlowAnalysisError",
    "CashFlowAnalysisMetadata",
    "CashFlowEngine",
    "CashFlowQualityFlag",
    "CashFlowTrendSummary",
    "CashQualityMetrics",
    "ConsistencyMetrics",
    "EquityMetrics",
    "ExpenseMetrics",
    "FinancingCashMetrics",
    "FinancialRatioAnalysis",
    "FinancialRatioEngine",
    "FinancialRatioError",
    "FinancialStatementsHistory",
    "FreeCashFlowMetrics",
    "GrowthInvestmentClass",
    "GrowthMetrics",
    "IncomeAnalysisError",
    "IncomeAnalysisMetadata",
    "IncomeStatementAnalysis",
    "IncomeStatementEngine",
    "InvestingCashMetrics",
    "LeverageMetrics",
    "LiabilityMetrics",
    "LiquidityMetrics",
    "MarginMetrics",
    "MetricExplanation",
    "MetricTrend",
    "OperatingCashMetrics",
    "ProfitabilityMetrics",
    "QualityFlag",
    "RatioAnalysisMetadata",
    "RatioMetric",
    "RatioQualityFlag",
    "RatioTrendSummary",
    "RevenueMetrics",
    "RevenueTrendClass",
    "TrendAnalysis",
    "TrendAnalysisError",
    "TrendAnalysisMetadata",
    "TrendClass",
    "TrendConsistencyMetrics",
    "TrendDirection",
    "TrendEngine",
    "TrendQualityFlag",
    "TrendSummary",
    "WorkingCapitalMetrics",
    "build_explanation",
    "validate_balance_for_analysis",
    "validate_cashflow_for_analysis",
    "validate_income_for_analysis",
    "validate_ratio_inputs",
    "validate_trend_history",
]
