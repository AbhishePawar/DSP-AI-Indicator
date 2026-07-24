"""Quantitative Risk Intelligence public API (E2.3 — models + engine + reporter)."""

from __future__ import annotations

from quantitative_risk.engine import EngineContext, EngineResult, QuantitativeRiskEngine
from quantitative_risk.enums import (
    EngineStatus,
    MetricStatus,
    MetricType,
    ReportingStatus,
    StressScenarioType,
)
from quantitative_risk.exceptions import QuantitativeRiskError
from quantitative_risk.models import (
    DrawdownProfile,
    QuantitativeRiskIdentity,
    QuantitativeRiskProfile,
    QuantitativeRiskReport,
    QuantitativeRiskSummary,
    RiskConcentration,
    RiskCorrelation,
    RiskDistribution,
    RiskExposure,
    RiskMetric,
    RiskVolatility,
    ScenarioResult,
    StressScenario,
)
from quantitative_risk.ports import (
    BenchmarkDataPort,
    HistoricalReturnsPort,
    MarketDataPort,
    ReturnPoint,
    WeightPoint,
)
from quantitative_risk.precision import (
    ANNUALIZATION_FACTOR_DAILY,
    METRIC_QUANTUM,
    RETURN_QUANTUM,
    WEIGHT_QUANTUM,
    quantize_metric,
    quantize_return,
    quantize_weight,
)
from quantitative_risk.refs import (
    BenchmarkReference,
    HistoricalReturnsReference,
    MarketDataReference,
    MonitoringReference,
    PortfolioReference,
    ResearchReference,
)
from quantitative_risk.reporter import (
    MetricCollection,
    QuantitativeRiskReporter,
    ReportMetadata,
    ReportingContext,
    ReportingResult,
)

__all__ = [
    "ANNUALIZATION_FACTOR_DAILY",
    "BenchmarkDataPort",
    "BenchmarkReference",
    "DrawdownProfile",
    "EngineContext",
    "EngineResult",
    "EngineStatus",
    "HistoricalReturnsPort",
    "HistoricalReturnsReference",
    "METRIC_QUANTUM",
    "MarketDataPort",
    "MarketDataReference",
    "MetricCollection",
    "MetricStatus",
    "MetricType",
    "MonitoringReference",
    "PortfolioReference",
    "QuantitativeRiskEngine",
    "QuantitativeRiskError",
    "QuantitativeRiskIdentity",
    "QuantitativeRiskProfile",
    "QuantitativeRiskReport",
    "QuantitativeRiskReporter",
    "QuantitativeRiskSummary",
    "RETURN_QUANTUM",
    "ReportMetadata",
    "ReportingContext",
    "ReportingResult",
    "ReportingStatus",
    "ResearchReference",
    "ReturnPoint",
    "RiskConcentration",
    "RiskCorrelation",
    "RiskDistribution",
    "RiskExposure",
    "RiskMetric",
    "RiskVolatility",
    "ScenarioResult",
    "StressScenario",
    "StressScenarioType",
    "WEIGHT_QUANTUM",
    "WeightPoint",
    "quantize_metric",
    "quantize_return",
    "quantize_weight",
]

__version__ = "0.3.0"
