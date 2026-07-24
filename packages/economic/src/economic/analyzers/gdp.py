"""GDP growth analyzer."""

from __future__ import annotations

from contracts.enums import SignalDirection

from economic.analyzers.base import Analyzer
from economic.models import EconomicSignal, EconomicSnapshot

__all__ = ["GdpAnalyzer"]

#: Strong real GDP growth threshold (3%).
_STRONG = 0.03
#: Weak / near-stall threshold (1%).
_WEAK = 0.01


class GdpAnalyzer(Analyzer):
    """Classifies GDP growth as strong, moderate, or weak."""

    @property
    def name(self) -> str:
        """Canonical analyzer identifier."""
        return "gdp"

    def analyze(self, snapshot: EconomicSnapshot) -> tuple[EconomicSignal, ...]:
        """Evaluate GDP growth against fixed thresholds."""
        value = snapshot.gdp_growth
        if value is None:
            return (
                EconomicSignal(
                    name="gdp",
                    direction=SignalDirection.NEUTRAL,
                    observation="GDP Unavailable",
                    reasoning="GDP growth was not reported in the snapshot.",
                    value=None,
                ),
            )
        if value >= _STRONG:
            return (
                EconomicSignal(
                    name="gdp",
                    direction=SignalDirection.BULLISH,
                    observation="Strong GDP Growth",
                    reasoning=(
                        f"GDP growth of {value:.1%} is at or above the "
                        f"{_STRONG:.0%} strong-growth threshold."
                    ),
                    value=value,
                    threshold=_STRONG,
                ),
            )
        if value >= _WEAK:
            return (
                EconomicSignal(
                    name="gdp",
                    direction=SignalDirection.NEUTRAL,
                    observation="Moderate GDP Growth",
                    reasoning=(
                        f"GDP growth of {value:.1%} is between the "
                        f"{_WEAK:.0%} and {_STRONG:.0%} thresholds."
                    ),
                    value=value,
                    threshold=_WEAK,
                ),
            )
        return (
            EconomicSignal(
                name="gdp",
                direction=SignalDirection.BEARISH,
                observation="Weak GDP Growth",
                reasoning=(
                    f"GDP growth of {value:.1%} is below the "
                    f"{_WEAK:.0%} weak-growth threshold."
                ),
                value=value,
                threshold=_WEAK,
            ),
        )
