"""Orchestration service for the Indicator Engine.

:class:`IndicatorEngine` is the platform-facing entry point described by
the architecture document's Section 3.4: it receives a
``contracts.PriceSeries``, runs the requested (or default) indicators
against it, and returns a fully explained, evidence-backed analysis —
without itself knowing how any individual indicator is calculated.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

import numpy as np

import dsp.registry as indicator_registry
from contracts.domain.price_series import PriceSeries
from dsp.engine.models import IndicatorResult, IndicatorSpec
from dsp.engine.results import AnalysisResult, IndicatorAnalysis
from dsp.exceptions import IndicatorError
from dsp.indicators.base import Indicator
from dsp.signals import rules
from dsp.signals.evidence_generator import EvidenceGenerator
from dsp.signals.explanation_generator import ExplanationGenerator
from dsp.signals.signal_generator import SignalGenerator

IndicatorResolver = Callable[[str, int], Indicator]
Clock = Callable[[], datetime]

#: Indicators run when a caller does not specify its own selection.
#: Chosen to exercise every existing indicator (SMA, EMA, WMA, RSI) with
#: a commonly used period, not as a recommended trading configuration.
DEFAULT_INDICATOR_SPECS: tuple[IndicatorSpec, ...] = (
    IndicatorSpec("sma", 20),
    IndicatorSpec("ema", 12),
    IndicatorSpec("wma", 20),
    IndicatorSpec("rsi", 14),
)


def _default_clock() -> datetime:
    """Return the current, timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class IndicatorEngine:
    """Orchestrates indicator computation, signal, and evidence generation.

    The engine's own logic is entirely generic: given a
    ``contracts.PriceSeries`` and a list of :class:`IndicatorSpec`
    requests, it resolves each named indicator through the existing
    registry, calls its unmodified ``compute()`` method, and hands the
    result to the signal/explanation/evidence generators. It never
    branches on a specific indicator name itself — that knowledge is
    confined to :mod:`dsp.signals.rules`.

    Every collaborator is injectable via the constructor (dependency
    inversion), so the engine can be tested with fake indicators, fake
    generators, or a fixed clock without touching the real registry or
    wall-clock time.
    """

    def __init__(
        self,
        *,
        resolve_indicator: IndicatorResolver = indicator_registry.get,
        signal_generator: SignalGenerator | None = None,
        explanation_generator: ExplanationGenerator | None = None,
        evidence_generator: EvidenceGenerator | None = None,
        clock: Clock = _default_clock,
    ) -> None:
        """Initialize the engine with its (optionally overridden) collaborators.

        Args:
            resolve_indicator: Callable resolving an indicator name and
                period to an :class:`~dsp.indicators.base.Indicator`
                instance. Defaults to the shared indicator registry.
            signal_generator: Component turning a rule outcome into a
                ``contracts.Signal``. Defaults to a new
                :class:`SignalGenerator`.
            explanation_generator: Component turning a rule outcome into
                a ``contracts.Explanation``. Defaults to a new
                :class:`ExplanationGenerator`.
            evidence_generator: Component turning a rule outcome into a
                ``contracts.Evidence`` item. Defaults to a new
                :class:`EvidenceGenerator`.
            clock: Callable returning the current timezone-aware
                timestamp, used only as execution metadata on each
                :class:`IndicatorResult`. Defaults to
                ``datetime.now(UTC)``.
        """
        self._resolve_indicator = resolve_indicator
        self._signal_generator = signal_generator or SignalGenerator()
        self._explanation_generator = explanation_generator or ExplanationGenerator()
        self._evidence_generator = evidence_generator or EvidenceGenerator()
        self._clock = clock

    def analyze(
        self,
        price_series: PriceSeries,
        *,
        specs: Sequence[IndicatorSpec] | None = None,
    ) -> AnalysisResult:
        """Analyze a price series and return a fully explained result.

        Args:
            price_series: The series to analyze. Never mutated.
            specs: Which indicators to run, with which periods. Defaults
                to :data:`DEFAULT_INDICATOR_SPECS` when omitted.

        Returns:
            A structured :class:`AnalysisResult` containing one
            ``Signal``/``Explanation``/``Evidence`` triple per requested
            indicator. No NumPy array leaves this method.

        Raises:
            IndicatorError: If any requested indicator name is not
                registered, its computation otherwise fails, or no
                signal rule is registered for it (see
                :mod:`dsp.signals.rules`).
        """
        selected = tuple(specs) if specs else DEFAULT_INDICATOR_SPECS
        analyses = tuple(self._analyze_one(price_series, spec) for spec in selected)
        return AnalysisResult(instrument=price_series.instrument, analyses=analyses)

    def _analyze_one(
        self, price_series: PriceSeries, spec: IndicatorSpec
    ) -> IndicatorAnalysis:
        """Run one indicator spec and build its full analysis triple."""
        result = self._compute(price_series, spec)
        try:
            outcome = rules.evaluate(result)
        except KeyError as exc:
            msg = f"No signal rule registered for indicator '{result.name}': {exc}"
            raise IndicatorError(msg) from exc
        explanation = self._explanation_generator.generate(result, outcome)
        signal = self._signal_generator.generate(
            result, outcome, explanation=explanation
        )
        evidence = self._evidence_generator.generate(result, outcome, explanation)
        return IndicatorAnalysis(
            result=result, signal=signal, explanation=explanation, evidence=evidence
        )

    def _compute(
        self, price_series: PriceSeries, spec: IndicatorSpec
    ) -> IndicatorResult:
        """Resolve and run one indicator, converting its output to tuples."""
        try:
            indicator = self._resolve_indicator(spec.name, spec.period)
        except KeyError as exc:
            msg = f"Cannot analyze with unknown indicator '{spec.name}': {exc}"
            raise IndicatorError(msg) from exc

        closes = tuple(bar.close for bar in price_series.bars)
        try:
            raw_values = indicator.compute(np.asarray(closes, dtype=np.float64))
        except Exception as exc:
            msg = f"{indicator.name} computation failed: {exc}"
            raise IndicatorError(msg) from exc

        values = tuple(float(value) for value in raw_values)
        latest_value = values[-1] if values else float("nan")

        return IndicatorResult(
            instrument=price_series.instrument,
            name=indicator.name,
            period=spec.period,
            frequency=price_series.frequency,
            source_values=closes,
            values=values,
            latest_value=latest_value,
            as_of=price_series.end.timestamp,
            computed_at=self._clock(),
        )
