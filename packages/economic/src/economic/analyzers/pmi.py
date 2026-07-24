"""Purchasing Managers' Index analyzer."""

from __future__ import annotations

from contracts.enums import SignalDirection

from economic.analyzers.base import Analyzer
from economic.models import EconomicSignal, EconomicSnapshot

__all__ = ["PmiAnalyzer"]

#: Strong expansion PMI.
_STRONG = 55.0
#: Expansion / contraction dividing line.
_NEUTRAL = 50.0
#: Soft / mild contraction floor.
_SOFT = 45.0


class PmiAnalyzer(Analyzer):
    """Classifies PMI as strong expansion, expansion, soft, or contraction."""

    @property
    def name(self) -> str:
        """Canonical analyzer identifier."""
        return "pmi"

    def analyze(self, snapshot: EconomicSnapshot) -> tuple[EconomicSignal, ...]:
        """Evaluate PMI against fixed index thresholds."""
        value = snapshot.pmi
        if value is None:
            return (
                EconomicSignal(
                    name="pmi",
                    direction=SignalDirection.NEUTRAL,
                    observation="PMI Unavailable",
                    reasoning="PMI was not reported in the snapshot.",
                    value=None,
                ),
            )
        if value >= _STRONG:
            return (
                EconomicSignal(
                    name="pmi",
                    direction=SignalDirection.BULLISH,
                    observation="Strong Expansion PMI",
                    reasoning=(
                        f"PMI of {value:.1f} is at or above the "
                        f"{_STRONG:.0f} strong-expansion threshold."
                    ),
                    value=value,
                    threshold=_STRONG,
                ),
            )
        if value >= _NEUTRAL:
            return (
                EconomicSignal(
                    name="pmi",
                    direction=SignalDirection.BULLISH,
                    observation="Expansion PMI",
                    reasoning=(
                        f"PMI of {value:.1f} is at or above the "
                        f"{_NEUTRAL:.0f} expansion threshold."
                    ),
                    value=value,
                    threshold=_NEUTRAL,
                ),
            )
        if value >= _SOFT:
            return (
                EconomicSignal(
                    name="pmi",
                    direction=SignalDirection.NEUTRAL,
                    observation="Soft PMI",
                    reasoning=(
                        f"PMI of {value:.1f} is between the {_SOFT:.0f} "
                        f"and {_NEUTRAL:.0f} thresholds."
                    ),
                    value=value,
                    threshold=_SOFT,
                ),
            )
        return (
            EconomicSignal(
                name="pmi",
                direction=SignalDirection.BEARISH,
                observation="Contraction PMI",
                reasoning=(
                    f"PMI of {value:.1f} is below the {_SOFT:.0f} "
                    "contraction threshold."
                ),
                value=value,
                threshold=_SOFT,
            ),
        )
