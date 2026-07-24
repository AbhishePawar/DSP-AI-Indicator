"""Indicator Engine public API.

As of Sprint 3.0, this package is more than a collection of indicator
algorithms: :class:`IndicatorEngine` orchestrates them against a
``contracts.PriceSeries`` and returns a fully explained, evidence-backed
:class:`AnalysisResult`. See ``packages/dsp/README.md`` for the full
``PriceSeries -> IndicatorEngine -> Signal -> Explanation -> Evidence``
flow. The individual indicator algorithms (``SMA``, ``EMA``, ``RSI``,
``WMA``) and the name-based registry are unchanged from prior sprints.
"""

from dsp.engine import (
    DEFAULT_INDICATOR_SPECS,
    AnalysisResult,
    IndicatorAnalysis,
    IndicatorEngine,
    IndicatorResult,
    IndicatorSpec,
)
from dsp.exceptions import IndicatorError
from dsp.indicators import EMA, RSI, SMA, WMA, Indicator, ema, rsi, sma, wma
from dsp.registry import compute, get, indicator_factory, list_indicators, register
from dsp.signals import EvidenceGenerator, ExplanationGenerator, SignalGenerator

__all__ = [
    "DEFAULT_INDICATOR_SPECS",
    "EMA",
    "AnalysisResult",
    "EvidenceGenerator",
    "ExplanationGenerator",
    "Indicator",
    "IndicatorAnalysis",
    "IndicatorEngine",
    "IndicatorError",
    "IndicatorResult",
    "IndicatorSpec",
    "RSI",
    "SMA",
    "SignalGenerator",
    "WMA",
    "compute",
    "ema",
    "get",
    "indicator_factory",
    "list_indicators",
    "register",
    "rsi",
    "sma",
    "wma",
]

__version__ = "0.2.0"
