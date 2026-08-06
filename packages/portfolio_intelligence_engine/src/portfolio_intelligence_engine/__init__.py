"""portfolio_intelligence_engine — RC1 Milestone 4.

A pure-Python combination/scoring layer that orchestrates already-computed
outputs from the frozen Valuation Engine, Risk Engine, Portfolio Analytics
module, and AI Committee (surfaced via ``dsp_platform``) into
portfolio-level intelligence. See the package README for the full data
honesty contract — this package never performs valuation, risk, or AI
computation itself.
"""

from __future__ import annotations

from portfolio_intelligence_engine.concentration import compute_concentration_analysis
from portfolio_intelligence_engine.diversification import compute_diversification_score
from portfolio_intelligence_engine.drift import compute_drift_analysis
from portfolio_intelligence_engine.enums import (
    AllocationKind,
    DriftDirection,
    IntelligenceStatus,
    RecommendationAction,
    ValuationClass,
)
from portfolio_intelligence_engine.exceptions import PortfolioIntelligenceEngineError
from portfolio_intelligence_engine.health_score import compute_health_score
from portfolio_intelligence_engine.models import (
    ConcentrationAnalysis,
    ConcentrationFlag,
    DiversificationScore,
    DriftAnalysis,
    DriftRow,
    HealthScoreResult,
    HealthSubScore,
    HoldingSignal,
    OpportunityEntry,
    OpportunityRanking,
    PortfolioRecommendation,
    PortfolioScenarioSummary,
    RiskHighlight,
    RiskSummary,
    ScenarioCase,
    ValuationHeatmap,
    ValuationHeatmapRow,
)
from portfolio_intelligence_engine.opportunities import rank_opportunities
from portfolio_intelligence_engine.recommendations import generate_recommendations
from portfolio_intelligence_engine.risk_summary import build_risk_summary
from portfolio_intelligence_engine.scenario import build_scenario_summary
from portfolio_intelligence_engine.valuation_heatmap import (
    classify_valuation,
    compute_valuation_heatmap,
)

__version__ = "0.1.0"

__all__ = [
    "AllocationKind",
    "ConcentrationAnalysis",
    "ConcentrationFlag",
    "DiversificationScore",
    "DriftAnalysis",
    "DriftDirection",
    "DriftRow",
    "HealthScoreResult",
    "HealthSubScore",
    "HoldingSignal",
    "IntelligenceStatus",
    "OpportunityEntry",
    "OpportunityRanking",
    "PortfolioIntelligenceEngineError",
    "PortfolioRecommendation",
    "PortfolioScenarioSummary",
    "RecommendationAction",
    "RiskHighlight",
    "RiskSummary",
    "ScenarioCase",
    "ValuationClass",
    "ValuationHeatmap",
    "ValuationHeatmapRow",
    "__version__",
    "build_risk_summary",
    "build_scenario_summary",
    "classify_valuation",
    "compute_concentration_analysis",
    "compute_diversification_score",
    "compute_drift_analysis",
    "compute_health_score",
    "compute_valuation_heatmap",
    "generate_recommendations",
    "rank_opportunities",
]
