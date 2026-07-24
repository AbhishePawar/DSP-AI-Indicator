"""Liquidity conditions analyzer."""

from __future__ import annotations

from contracts.enums import SignalDirection

from economic.analyzers.base import Analyzer
from economic.models import EconomicSignal, EconomicSnapshot

__all__ = ["LiquidityAnalyzer"]

#: Ample liquidity floor.
_AMPLE = 0.6
#: Adequate liquidity floor.
_ADEQUATE = 0.4


class LiquidityAnalyzer(Analyzer):
    """Classifies liquidity as ample, adequate, or tight."""

    @property
    def name(self) -> str:
        """Canonical analyzer identifier."""
        return "liquidity"

    def analyze(self, snapshot: EconomicSnapshot) -> tuple[EconomicSignal, ...]:
        """Evaluate the normalized liquidity indicator."""
        value = snapshot.liquidity_indicator
        if value is None:
            return (
                EconomicSignal(
                    name="liquidity",
                    direction=SignalDirection.NEUTRAL,
                    observation="Liquidity Unavailable",
                    reasoning=(
                        "Liquidity indicator was not reported in the "
                        "snapshot."
                    ),
                    value=None,
                ),
            )
        if value >= _AMPLE:
            return (
                EconomicSignal(
                    name="liquidity",
                    direction=SignalDirection.BULLISH,
                    observation="Ample Liquidity",
                    reasoning=(
                        f"Liquidity indicator of {value:.2f} is at or "
                        f"above the {_AMPLE:.2f} ample-liquidity "
                        "threshold."
                    ),
                    value=value,
                    threshold=_AMPLE,
                ),
            )
        if value >= _ADEQUATE:
            return (
                EconomicSignal(
                    name="liquidity",
                    direction=SignalDirection.NEUTRAL,
                    observation="Adequate Liquidity",
                    reasoning=(
                        f"Liquidity indicator of {value:.2f} is between "
                        f"the {_ADEQUATE:.2f} and {_AMPLE:.2f} thresholds."
                    ),
                    value=value,
                    threshold=_ADEQUATE,
                ),
            )
        return (
            EconomicSignal(
                name="liquidity",
                direction=SignalDirection.BEARISH,
                observation="Tight Liquidity",
                reasoning=(
                    f"Liquidity indicator of {value:.2f} is below the "
                    f"{_ADEQUATE:.2f} tight-liquidity threshold."
                ),
                value=value,
                threshold=_ADEQUATE,
            ),
        )
