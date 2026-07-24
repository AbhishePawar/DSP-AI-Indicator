"""Orchestration layer for the Indicator Engine.

This is the platform's "application layer" (Section 5.2 of the
architecture document) for indicators: it receives a
``contracts.PriceSeries``, decides which indicators to run, executes them
through the existing, unmodified registry, and returns a structured,
fully explained analysis. It contains no indicator math of its own — see
:mod:`dsp.indicators` for that — and no rule-specific knowledge — see
:mod:`dsp.signals` for that.
"""

from dsp.engine.models import IndicatorResult, IndicatorSpec
from dsp.engine.results import AnalysisResult, IndicatorAnalysis
from dsp.engine.service import DEFAULT_INDICATOR_SPECS, IndicatorEngine

__all__ = [
    "DEFAULT_INDICATOR_SPECS",
    "AnalysisResult",
    "IndicatorAnalysis",
    "IndicatorEngine",
    "IndicatorResult",
    "IndicatorSpec",
]
