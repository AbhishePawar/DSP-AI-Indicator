"""Structured analysis output of the Fundamental Engine.

:class:`CompanyAnalysis` is what
:meth:`fundamental.engine.service.FundamentalEngine.analyze` returns. It
bundles one :class:`MetricAnalysis` per metric produced across every
requested analyzer, each carrying the ``contracts.Signal`` /
``contracts.Explanation`` / ``contracts.Evidence`` triple produced for
that metric, plus the per-analyzer :class:`FundamentalResult` objects
for introspection. This mirrors ``dsp.engine.results`` exactly, with one
addition: because one analyzer can produce several related metrics at
once (e.g. profitability), ``CompanyAnalysis`` keeps both the
per-analyzer results and the flattened per-metric analyses.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts.domain.evidence import Evidence
from contracts.domain.explanation import Explanation
from contracts.domain.instrument import Instrument
from contracts.domain.signal import Signal
from fundamental.models import FundamentalMetric, FundamentalResult


@dataclass(frozen=True, slots=True)
class MetricAnalysis:
    """The complete analytical output for one computed metric.

    Attributes:
        metric: The internal computation this analysis was derived from.
            Not a ``contracts`` type — see
            :class:`~fundamental.models.FundamentalMetric`.
        signal: The directional business reading produced for this
            metric.
        explanation: Human-readable rationale behind ``signal``.
        evidence: Discrete supporting fact citing ``signal`` and
            ``explanation``, suitable for use by downstream engines (e.g.
            the future AI Investment Committee).
    """

    metric: FundamentalMetric
    signal: Signal
    explanation: Explanation
    evidence: Evidence


@dataclass(frozen=True, slots=True)
class CompanyAnalysis:
    """The Fundamental Engine's complete output for one financial snapshot.

    Attributes:
        instrument: The instrument that was analyzed.
        results: One :class:`~fundamental.models.FundamentalResult`
            per analyzer that ran, in the order the analyzers were
            requested. Kept for introspection and traceability of which
            analyzer produced which metrics.
        analyses: One :class:`MetricAnalysis` per metric produced across
            every requested analyzer, in the same order as ``results``.
    """

    instrument: Instrument
    results: tuple[FundamentalResult, ...]
    analyses: tuple[MetricAnalysis, ...]

    @property
    def signals(self) -> tuple[Signal, ...]:
        """Return every produced signal, in analysis order."""
        return tuple(analysis.signal for analysis in self.analyses)

    @property
    def explanations(self) -> tuple[Explanation, ...]:
        """Return every produced explanation, in analysis order."""
        return tuple(analysis.explanation for analysis in self.analyses)

    @property
    def evidence(self) -> tuple[Evidence, ...]:
        """Return every produced evidence item, in analysis order."""
        return tuple(analysis.evidence for analysis in self.analyses)
