"""Converts a rule's conclusion into a ``contracts.Evidence`` item."""

from __future__ import annotations

import math

from contracts.domain.evidence import Evidence
from contracts.domain.explanation import Explanation
from contracts.enums import EngineSource
from dsp.engine.models import IndicatorResult
from dsp.signals.rules import RuleOutcome


class EvidenceGenerator:
    """Builds a ``contracts.Evidence`` item citing an indicator reading.

    ``Evidence`` is the shape downstream engines (ultimately the AI
    Investment Committee) cite as a discrete supporting fact for a
    broader decision. It carries the same reasoning as the signal and
    explanation, plus an explicit reference to the indicator and
    threshold involved, so the fact can be checked independently of the
    ``Signal``/``Explanation`` pair it was generated alongside.
    """

    def generate(
        self,
        result: IndicatorResult,
        outcome: RuleOutcome,
        explanation: Explanation | None = None,
    ) -> Evidence:
        """Build an ``Evidence`` item for one indicator's rule outcome.

        Args:
            result: The indicator computation the evidence is about.
            outcome: The rule's directional conclusion for ``result``.
            explanation: Optional explanation to embed on the evidence.

        Returns:
            An immutable ``contracts.Evidence`` citing the indicator,
            its latest value, the threshold (if any) it was compared
            against, and the reasoning behind the comparison.
        """
        value = result.latest_value
        return Evidence(
            source_engine=EngineSource.INDICATOR_ENGINE,
            claim=outcome.reasoning,
            value=None if math.isnan(value) else value,
            reference=result.label,
            explanation=explanation,
            weight=outcome.strength,
        )
