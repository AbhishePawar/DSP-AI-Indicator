"""Fundamental Engine public API.

The Fundamental Engine is the platform's Business Analysis layer:
:class:`FundamentalEngine` orchestrates a set of pluggable analyzers
against a :class:`FinancialSnapshot` (a validated bundle of
``contracts.FundamentalStatement`` periods for one instrument) and
returns a fully explained, evidence-backed :class:`CompanyAnalysis`. See
``packages/fundamental/README.md`` for the full ``FinancialSnapshot ->
FundamentalEngine -> Analyzer -> FundamentalResult -> Signal ->
Explanation -> Evidence`` flow.
"""

from fundamental.analyzers import (
    Analyzer,
    GrowthAnalyzer,
    LeverageAnalyzer,
    ProfitabilityAnalyzer,
    QualityAnalyzer,
)
from fundamental.engine import (
    DEFAULT_ANALYZER_NAMES,
    CompanyAnalysis,
    FinancialSnapshot,
    FundamentalEngine,
    FundamentalMetric,
    FundamentalResult,
    MetricAnalysis,
)
from fundamental.enums import MetricUnit
from fundamental.exceptions import FundamentalError
from fundamental.registry import get, list_analyzers, register
from fundamental.signals import (
    BusinessRuleOutcome,
    BusinessSignalGenerator,
    EvidenceGenerator,
    ExplanationGenerator,
    evaluate,
    register_rule,
)

__all__ = [
    "DEFAULT_ANALYZER_NAMES",
    "Analyzer",
    "BusinessRuleOutcome",
    "BusinessSignalGenerator",
    "CompanyAnalysis",
    "EvidenceGenerator",
    "ExplanationGenerator",
    "FinancialSnapshot",
    "FundamentalEngine",
    "FundamentalError",
    "FundamentalMetric",
    "FundamentalResult",
    "GrowthAnalyzer",
    "LeverageAnalyzer",
    "MetricAnalysis",
    "MetricUnit",
    "ProfitabilityAnalyzer",
    "QualityAnalyzer",
    "evaluate",
    "get",
    "list_analyzers",
    "register",
    "register_rule",
]

__version__ = "0.1.0"
