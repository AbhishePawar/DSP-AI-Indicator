"""Converts a :class:`FundamentalMetric` into a ``contracts.Signal``.

The mission's "Business Signals" (e.g. "Strong Profitability", "High
Debt") are not a new Contracts type — reusing ``contracts.Signal`` is
the correct fit and keeps Contracts stable, exactly as ``dsp`` already
does for indicator readings. ``SignalDirection`` is a business
observation here, not an investment recommendation; that distinction is
Fundamental Engine convention, not a difference in the underlying type.
"""

from __future__ import annotations

from datetime import UTC, datetime, time

from contracts.domain.explanation import Explanation
from contracts.domain.signal import Signal
from contracts.enums import EngineSource
from fundamental.models import FundamentalMetric
from fundamental.signals.rules import BusinessRuleOutcome


def _as_of(metric: FundamentalMetric) -> datetime:
    """Convert a metric's reporting date into a timezone-aware timestamp."""
    return datetime.combine(metric.period_end, time.min, tzinfo=UTC)


class BusinessSignalGenerator:
    """Builds a ``contracts.Signal`` from a rule's directional conclusion.

    This class holds no metric-specific knowledge — that lives entirely
    in :mod:`fundamental.signals.rules`. Its only responsibility is
    shaping an already-decided :class:`BusinessRuleOutcome` into the
    platform's shared ``Signal`` contract.
    """

    def generate(
        self,
        metric: FundamentalMetric,
        outcome: BusinessRuleOutcome,
        *,
        explanation: Explanation | None = None,
    ) -> Signal:
        """Build a ``Signal`` for one metric's computation.

        Args:
            metric: The metric the signal is about.
            outcome: The rule's directional conclusion for ``metric``.
            explanation: Optional explanation to embed on the signal.

        Returns:
            An immutable ``contracts.Signal`` describing the reading.
        """
        return Signal(
            instrument=metric.instrument,
            source_engine=EngineSource.FUNDAMENTAL_ENGINE,
            name=metric.name,
            direction=outcome.direction,
            timestamp=_as_of(metric),
            value=metric.value,
            strength=outcome.strength,
            explanation=explanation,
        )
