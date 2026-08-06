"""Portfolio Intelligence Engine façade (RC1 Milestone 4).

Public entry point re-exported by ``dsp_platform.platform.DSPPlatform``. See
``dsp_platform.portfolio_intelligence_engine.service`` for the orchestration.
"""

from __future__ import annotations

from dsp_platform.portfolio_intelligence_engine.service import (
    PORTFOLIO_INTELLIGENCE_ENGINE_SERVICE_VERSION,
    evaluate_portfolio_health,
    evaluate_portfolio_intelligence_engine,
    evaluate_portfolio_opportunities,
    evaluate_portfolio_recommendations,
    evaluate_portfolio_scenario,
    portfolio_intelligence_engine_health,
)

__all__ = [
    "PORTFOLIO_INTELLIGENCE_ENGINE_SERVICE_VERSION",
    "evaluate_portfolio_health",
    "evaluate_portfolio_intelligence_engine",
    "evaluate_portfolio_opportunities",
    "evaluate_portfolio_recommendations",
    "evaluate_portfolio_scenario",
    "portfolio_intelligence_engine_health",
]
