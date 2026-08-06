"""portfolio_analytics — Portfolio Intelligence Analytics engine (additive).

Pure computation, Ports & Adapters, no I/O. See ``README.md`` for scope and
the reuse table (Max Drawdown reused from ``quantitative_risk``; Sector
Allocation is a parallel implementation since ``portfolio`` is frozen).
"""

from __future__ import annotations

from portfolio_analytics.allocation import (
    EXCHANGE_COUNTRY_TABLE,
    compute_country_allocation,
    compute_sector_allocation,
)
from portfolio_analytics.constraints import (
    check_position_limits,
    compute_rebalancing_plan,
)
from portfolio_analytics.correlation import (
    build_correlation_matrix,
    build_heatmap,
    compute_correlation,
)
from portfolio_analytics.enums import (
    AllocationDimension,
    AnalyticsStatus,
    RebalancingAction,
    TaxTerm,
)
from portfolio_analytics.exceptions import PortfolioAnalyticsError
from portfolio_analytics.factor_exposure import compute_factor_exposures
from portfolio_analytics.models import (
    AllocationBreakdown,
    AllocationBucket,
    CorrelationMatrix,
    EfficientFrontierPoint,
    EfficientFrontierResult,
    FactorExposure,
    FactorExposureProfile,
    HeatmapCell,
    MonteCarloSummary,
    PerformanceRatios,
    PositionInput,
    PositionLimitBreach,
    PositionLimitReport,
    RebalancingPlan,
    RebalancingTrade,
    RiskAttributionProfile,
    RiskAttributionRow,
    ScenarioImpact,
    StressTestResult,
    TaxLotAnalysis,
    TaxReport,
)
from portfolio_analytics.performance import (
    compute_alpha,
    compute_beta,
    compute_information_ratio,
    compute_max_drawdown_via_quantitative_risk,
    compute_performance_ratios,
    compute_sharpe_ratio,
    compute_sortino_ratio,
    compute_tracking_error,
    compute_treynor_ratio,
)
from portfolio_analytics.ports import DailyReturn, PriceHistoryPort
from portfolio_analytics.returns import (
    AlignedReturns,
    align_return_series,
    weighted_series,
)
from portfolio_analytics.risk_attribution import compute_risk_attribution
from portfolio_analytics.simulation import (
    compute_efficient_frontier,
    compute_monte_carlo,
)
from portfolio_analytics.stress import (
    compute_scenario_impact,
    compute_stress_test,
    cumulative_window_return,
)
from portfolio_analytics.tax import compute_tax_report

__all__ = [
    "EXCHANGE_COUNTRY_TABLE",
    "AlignedReturns",
    "AllocationBreakdown",
    "AllocationBucket",
    "AllocationDimension",
    "AnalyticsStatus",
    "CorrelationMatrix",
    "DailyReturn",
    "EfficientFrontierPoint",
    "EfficientFrontierResult",
    "FactorExposure",
    "FactorExposureProfile",
    "HeatmapCell",
    "MonteCarloSummary",
    "PerformanceRatios",
    "PortfolioAnalyticsError",
    "PositionInput",
    "PositionLimitBreach",
    "PositionLimitReport",
    "PriceHistoryPort",
    "RebalancingAction",
    "RebalancingPlan",
    "RebalancingTrade",
    "RiskAttributionProfile",
    "RiskAttributionRow",
    "ScenarioImpact",
    "StressTestResult",
    "TaxLotAnalysis",
    "TaxReport",
    "TaxTerm",
    "align_return_series",
    "build_correlation_matrix",
    "build_heatmap",
    "check_position_limits",
    "compute_alpha",
    "compute_beta",
    "compute_country_allocation",
    "compute_correlation",
    "compute_efficient_frontier",
    "compute_factor_exposures",
    "compute_information_ratio",
    "compute_max_drawdown_via_quantitative_risk",
    "compute_monte_carlo",
    "compute_performance_ratios",
    "compute_rebalancing_plan",
    "compute_risk_attribution",
    "compute_scenario_impact",
    "compute_sector_allocation",
    "compute_sharpe_ratio",
    "compute_sortino_ratio",
    "compute_stress_test",
    "compute_tax_report",
    "compute_tracking_error",
    "compute_treynor_ratio",
    "cumulative_window_return",
    "weighted_series",
]

__version__ = "0.1.0"
