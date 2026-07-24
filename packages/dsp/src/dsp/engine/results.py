"""Structured analysis output of the Indicator Engine.

:class:`AnalysisResult` is what
:meth:`dsp.engine.service.IndicatorEngine.analyze` returns. It bundles one
:class:`IndicatorAnalysis` per requested ``IndicatorSpec`` (see
:mod:`dsp.engine.models`), each carrying the ``contracts.Signal`` /
``contracts.Explanation`` / ``contracts.Evidence`` triple produced for
that indicator, plus the internal ``IndicatorResult`` it was derived
from for introspection.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts.domain.evidence import Evidence
from contracts.domain.explanation import Explanation
from contracts.domain.instrument import Instrument
from contracts.domain.signal import Signal
from dsp.engine.models import IndicatorResult


@dataclass(frozen=True, slots=True)
class IndicatorAnalysis:
    """The complete analytical output for one requested indicator.

    Attributes:
        result: The internal computation this analysis was derived from.
            Not a ``contracts`` type — see
            :class:`~dsp.engine.models.IndicatorResult`.
        signal: The directional reading produced for this indicator.
        explanation: Human-readable rationale behind ``signal``.
        evidence: Discrete supporting fact citing ``signal`` and
            ``explanation``, suitable for use by downstream engines (e.g.
            the future AI Investment Committee).
    """

    result: IndicatorResult
    signal: Signal
    explanation: Explanation
    evidence: Evidence


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """The Indicator Engine's complete output for one price series.

    Attributes:
        instrument: The instrument that was analyzed.
        analyses: One :class:`IndicatorAnalysis` per requested indicator,
            in the order the indicators were requested.
    """

    instrument: Instrument
    analyses: tuple[IndicatorAnalysis, ...]

    @property
    def signals(self) -> tuple[Signal, ...]:
        """Return every produced signal, in request order."""
        return tuple(analysis.signal for analysis in self.analyses)

    @property
    def explanations(self) -> tuple[Explanation, ...]:
        """Return every produced explanation, in request order."""
        return tuple(analysis.explanation for analysis in self.analyses)

    @property
    def evidence(self) -> tuple[Evidence, ...]:
        """Return every produced evidence item, in request order."""
        return tuple(analysis.evidence for analysis in self.analyses)
