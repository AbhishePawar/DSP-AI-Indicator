"""Portfolio Intelligence Analytics façade (dsp_platform composition layer).

Thin wrapper over the additive ``portfolio_analytics`` pure engine, wired to
authenticated price history via ``dsp_platform.historical_series``. See
``docs/PORTFOLIO_ANALYTICS.md``.
"""

from __future__ import annotations

from dsp_platform.portfolio_analytics.adapter import HistoricalSeriesPriceHistoryAdapter
from dsp_platform.portfolio_analytics.service import (
    PORTFOLIO_ANALYTICS_SERVICE_VERSION,
    STRESS_WINDOW_CATALOG,
    evaluate_portfolio_allocation_analytics,
    evaluate_portfolio_constraints,
    evaluate_portfolio_performance,
    evaluate_portfolio_risk_analytics,
    evaluate_portfolio_simulation,
    evaluate_portfolio_stress_analytics,
    evaluate_portfolio_tax_analytics,
    portfolio_analytics_health,
    portfolio_analytics_metrics,
)

__all__ = [
    "PORTFOLIO_ANALYTICS_SERVICE_VERSION",
    "STRESS_WINDOW_CATALOG",
    "HistoricalSeriesPriceHistoryAdapter",
    "evaluate_portfolio_allocation_analytics",
    "evaluate_portfolio_constraints",
    "evaluate_portfolio_performance",
    "evaluate_portfolio_risk_analytics",
    "evaluate_portfolio_simulation",
    "evaluate_portfolio_stress_analytics",
    "evaluate_portfolio_tax_analytics",
    "portfolio_analytics_health",
    "portfolio_analytics_metrics",
]
