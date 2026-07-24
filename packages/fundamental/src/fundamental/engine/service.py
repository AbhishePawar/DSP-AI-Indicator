"""Orchestration service for the Fundamental Engine.

:class:`FundamentalEngine` is the platform-facing entry point for
business-fundamentals analysis: it receives a :class:`FinancialSnapshot`,
runs the requested (or default) analyzers against it, and returns a
fully explained, evidence-backed :class:`CompanyAnalysis` — without
itself knowing how any individual ratio is calculated. Mirrors
``dsp.engine.service.IndicatorEngine`` exactly.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

import fundamental.registry as analyzer_registry
from fundamental.analyzers.base import Analyzer
from fundamental.engine.results import CompanyAnalysis, MetricAnalysis
from fundamental.exceptions import FundamentalError
from fundamental.models import FinancialSnapshot, FundamentalMetric, FundamentalResult
from fundamental.signals import rules
from fundamental.signals.evidence_generator import EvidenceGenerator
from fundamental.signals.explanation_generator import ExplanationGenerator
from fundamental.signals.signal_generator import BusinessSignalGenerator

AnalyzerResolver = Callable[[str], Analyzer]
Clock = Callable[[], datetime]

#: Analyzers run when a caller does not specify its own selection.
#: Chosen to exercise every analyzer implemented in this sprint
#: (profitability, growth, leverage, quality), not as a recommended or
#: exhaustive set of business-analysis dimensions.
DEFAULT_ANALYZER_NAMES: tuple[str, ...] = (
    "profitability",
    "growth",
    "leverage",
    "quality",
)


def _default_clock() -> datetime:
    """Return the current, timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class FundamentalEngine:
    """Orchestrates analyzer execution, signal, and evidence generation.

    The engine's own logic is entirely generic: given a
    :class:`FinancialSnapshot` and a list of analyzer names, it resolves
    each named analyzer through the registry, calls its unmodified
    ``analyze()`` method, and hands each produced metric to the
    signal/explanation/evidence generators. It never branches on a
    specific metric or analyzer name itself — that knowledge is confined
    to :mod:`fundamental.signals.rules`.

    Every collaborator is injectable via the constructor (dependency
    inversion), so the engine can be tested with fake analyzers, fake
    generators, or a fixed clock without touching the real registry or
    wall-clock time.
    """

    def __init__(
        self,
        *,
        resolve_analyzer: AnalyzerResolver = analyzer_registry.get,
        signal_generator: BusinessSignalGenerator | None = None,
        explanation_generator: ExplanationGenerator | None = None,
        evidence_generator: EvidenceGenerator | None = None,
        clock: Clock = _default_clock,
    ) -> None:
        """Initialize the engine with its (optionally overridden) collaborators.

        Args:
            resolve_analyzer: Callable resolving an analyzer name to an
                :class:`~fundamental.analyzers.base.Analyzer` instance.
                Defaults to the shared analyzer registry.
            signal_generator: Component turning a rule outcome into a
                ``contracts.Signal``. Defaults to a new
                :class:`BusinessSignalGenerator`.
            explanation_generator: Component turning a rule outcome into
                a ``contracts.Explanation``. Defaults to a new
                :class:`ExplanationGenerator`.
            evidence_generator: Component turning a rule outcome into a
                ``contracts.Evidence`` item. Defaults to a new
                :class:`EvidenceGenerator`.
            clock: Callable returning the current timezone-aware
                timestamp, used only as execution metadata on each
                :class:`FundamentalResult`. Defaults to
                ``datetime.now(UTC)``.
        """
        self._resolve_analyzer = resolve_analyzer
        self._signal_generator = signal_generator or BusinessSignalGenerator()
        self._explanation_generator = explanation_generator or ExplanationGenerator()
        self._evidence_generator = evidence_generator or EvidenceGenerator()
        self._clock = clock

    def analyze(
        self,
        snapshot: FinancialSnapshot,
        *,
        analyzer_names: Sequence[str] | None = None,
    ) -> CompanyAnalysis:
        """Analyze a financial snapshot and return a fully explained result.

        Args:
            snapshot: The financial statements to analyze. Never
                mutated.
            analyzer_names: Which analyzers to run. Defaults to
                :data:`DEFAULT_ANALYZER_NAMES` when omitted.

        Returns:
            A structured :class:`CompanyAnalysis` containing one
            ``Signal``/``Explanation``/``Evidence`` triple per metric
            produced by every requested analyzer.

        Raises:
            FundamentalError: If any requested analyzer name is not
                registered, its execution otherwise fails, or no
                business rule is registered for a metric it produced
                (see :mod:`fundamental.signals.rules`).
        """
        selected = tuple(analyzer_names) if analyzer_names else DEFAULT_ANALYZER_NAMES
        results = tuple(self._run_analyzer(snapshot, name) for name in selected)
        analyses = tuple(
            self._analyze_metric(result, metric)
            for result in results
            for metric in result.metrics
        )
        return CompanyAnalysis(
            instrument=snapshot.instrument, results=results, analyses=analyses
        )

    def _run_analyzer(
        self, snapshot: FinancialSnapshot, name: str
    ) -> FundamentalResult:
        """Resolve and run one analyzer, stamping execution metadata."""
        try:
            analyzer = self._resolve_analyzer(name)
        except KeyError as exc:
            msg = f"Cannot analyze with unknown analyzer '{name}': {exc}"
            raise FundamentalError(msg) from exc

        try:
            metrics = analyzer.analyze(snapshot)
        except Exception as exc:
            msg = f"{analyzer.name} analysis failed: {exc}"
            raise FundamentalError(msg) from exc

        return FundamentalResult(
            instrument=snapshot.instrument,
            analyzer_name=analyzer.name,
            metrics=tuple(metrics),
            computed_at=self._clock(),
        )

    def _analyze_metric(
        self, result: FundamentalResult, metric: FundamentalMetric
    ) -> MetricAnalysis:
        """Evaluate one metric's business rule and build its analysis triple."""
        try:
            outcome = rules.evaluate(metric)
        except KeyError as exc:
            msg = f"No business rule registered for metric '{metric.name}': {exc}"
            raise FundamentalError(msg) from exc

        explanation = self._explanation_generator.generate(
            metric, outcome, generated_at=result.computed_at
        )
        signal = self._signal_generator.generate(
            metric, outcome, explanation=explanation
        )
        evidence = self._evidence_generator.generate(metric, outcome, explanation)
        return MetricAnalysis(
            metric=metric, signal=signal, explanation=explanation, evidence=evidence
        )
