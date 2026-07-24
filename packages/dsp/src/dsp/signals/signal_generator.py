"""Converts an :class:`IndicatorResult` into a ``contracts.Signal``."""

from __future__ import annotations

import math

from contracts.domain.explanation import Explanation
from contracts.domain.signal import Signal
from contracts.enums import EngineSource
from dsp.engine.models import IndicatorResult
from dsp.signals.rules import RuleOutcome


class SignalGenerator:
    """Builds a ``contracts.Signal`` from a rule's directional conclusion.

    This class holds no indicator-specific knowledge — that lives entirely
    in :mod:`dsp.signals.rules`. Its only responsibility is shaping an
    already-decided :class:`RuleOutcome` into the platform's shared
    ``Signal`` contract.
    """

    def generate(
        self,
        result: IndicatorResult,
        outcome: RuleOutcome,
        *,
        explanation: Explanation | None = None,
    ) -> Signal:
        """Build a ``Signal`` for one indicator's computation.

        Args:
            result: The indicator computation the signal is about.
            outcome: The rule's directional conclusion for ``result``.
            explanation: Optional explanation to embed on the signal.

        Returns:
            An immutable ``contracts.Signal`` describing the reading.
        """
        value = result.latest_value
        return Signal(
            instrument=result.instrument,
            source_engine=EngineSource.INDICATOR_ENGINE,
            name=f"{result.name}_{result.period}",
            direction=outcome.direction,
            timestamp=result.as_of,
            value=None if math.isnan(value) else value,
            strength=outcome.strength,
            explanation=explanation,
        )
