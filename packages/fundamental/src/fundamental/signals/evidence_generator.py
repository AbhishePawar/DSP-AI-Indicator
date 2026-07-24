"""Converts a rule's conclusion into a ``contracts.Evidence`` item."""

from __future__ import annotations

from contracts.domain.evidence import Evidence
from contracts.domain.explanation import Explanation
from contracts.enums import EngineSource
from fundamental.models import FundamentalMetric
from fundamental.signals.rules import BusinessRuleOutcome


class EvidenceGenerator:
    """Builds a ``contracts.Evidence`` item citing a fundamental metric.

    ``Evidence`` is the shape downstream engines (ultimately the AI
    Investment Committee) cite as a discrete supporting fact for a
    broader decision. It carries the same reasoning as the signal and
    explanation, plus an explicit reference to the metric and threshold
    involved, so the fact can be checked independently of the
    ``Signal``/``Explanation`` pair it was generated alongside. Mirrors
    ``dsp.signals.evidence_generator`` exactly.
    """

    def generate(
        self,
        metric: FundamentalMetric,
        outcome: BusinessRuleOutcome,
        explanation: Explanation | None = None,
    ) -> Evidence:
        """Build an ``Evidence`` item for one metric's rule outcome.

        Args:
            metric: The metric the evidence is about.
            outcome: The rule's directional conclusion for ``metric``.
            explanation: Optional explanation to embed on the evidence.

        Returns:
            An immutable ``contracts.Evidence`` citing the metric, its
            value, the threshold (if any) it was compared against, and
            the reasoning behind the comparison.
        """
        return Evidence(
            source_engine=EngineSource.FUNDAMENTAL_ENGINE,
            claim=outcome.reasoning,
            value=metric.value,
            reference=metric.label,
            explanation=explanation,
            weight=outcome.strength,
        )
