"""Converts a rule's conclusion into a ``contracts.Explanation``."""

from __future__ import annotations

from contracts.domain.explanation import Explanation
from contracts.enums import EngineSource
from dsp.engine.models import IndicatorResult
from dsp.signals.rules import RuleOutcome


class ExplanationGenerator:
    """Builds a human-readable ``contracts.Explanation`` for a signal.

    The explanation's ``summary`` is exactly the rule's ``reasoning`` —
    this generator's job is to attach provenance (which engine, which
    inputs, when) around that sentence, not to re-derive or rephrase the
    reasoning itself, so a signal and its explanation can never drift out
    of sync.
    """

    def generate(self, result: IndicatorResult, outcome: RuleOutcome) -> Explanation:
        """Build an ``Explanation`` for one indicator's rule outcome.

        Args:
            result: The indicator computation the explanation is about.
            outcome: The rule's directional conclusion for ``result``.

        Returns:
            An immutable ``contracts.Explanation`` describing why the
            signal has the direction and value it has.
        """
        return Explanation(
            source_engine=EngineSource.INDICATOR_ENGINE,
            summary=outcome.reasoning,
            inputs_used=(result.label, "close_price"),
            detail=None,
            confidence=outcome.strength,
            generated_at=result.computed_at,
        )
