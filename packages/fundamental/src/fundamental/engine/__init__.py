"""Orchestration layer for the Fundamental Engine.

This is the platform's "application layer" (Section 5.2 of the
architecture document) for business fundamentals: it receives a
:class:`FinancialSnapshot`, decides which analyzers to run, executes
them through the registry, and returns a structured, fully explained
analysis. It contains no ratio math of its own — see
:mod:`fundamental.analyzers` for that — and no rule-specific knowledge —
see :mod:`fundamental.signals` for that.
"""

from fundamental.engine.results import CompanyAnalysis, MetricAnalysis
from fundamental.engine.service import DEFAULT_ANALYZER_NAMES, FundamentalEngine
from fundamental.models import FinancialSnapshot, FundamentalMetric, FundamentalResult

__all__ = [
    "DEFAULT_ANALYZER_NAMES",
    "CompanyAnalysis",
    "FinancialSnapshot",
    "FundamentalEngine",
    "FundamentalMetric",
    "FundamentalResult",
    "MetricAnalysis",
]
