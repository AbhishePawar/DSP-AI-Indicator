"""Converts a rule's conclusion into a ``contracts.Explanation``."""

from __future__ import annotations

from datetime import datetime

from contracts.domain.explanation import Explanation
from contracts.enums import EngineSource
from fundamental.models import FundamentalMetric
from fundamental.signals.rules import BusinessRuleOutcome


class ExplanationGenerator:
    """Builds a human-readable ``contracts.Explanation`` for a signal.

    The explanation's ``summary`` is exactly the rule's ``reasoning`` —
    this generator's job is to attach provenance (which engine, which
    inputs, when) around that sentence, not to re-derive or rephrase the
    reasoning itself, so a signal and its explanation can never drift
    out of sync. Mirrors ``dsp.signals.explanation_generator`` exactly.

    Unlike the Indicator Engine's version, this generator takes
    ``generated_at`` explicitly rather than reading it off ``metric`` —
    a single analyzer run produces several metrics that share one
    execution timestamp (``FundamentalResult.computed_at``), so the
    timestamp is a run-level fact the engine threads through rather
    than a per-metric field. The generator itself holds no clock and no
    other state.
    """

    def generate(
        self,
        metric: FundamentalMetric,
        outcome: BusinessRuleOutcome,
        *,
        generated_at: datetime,
    ) -> Explanation:
        """Build an ``Explanation`` for one metric's rule outcome.

        Args:
            metric: The metric the explanation is about.
            outcome: The rule's directional conclusion for ``metric``.
            generated_at: Timezone-aware timestamp of when the
                analyzer run that produced ``metric`` executed.

        Returns:
            An immutable ``contracts.Explanation`` describing why the
            signal has the direction and value it has.
        """
        return Explanation(
            source_engine=EngineSource.FUNDAMENTAL_ENGINE,
            summary=outcome.reasoning,
            inputs_used=(metric.label, outcome.observation),
            detail=None,
            confidence=outcome.strength,
            generated_at=generated_at,
        )
