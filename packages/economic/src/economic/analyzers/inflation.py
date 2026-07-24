"""CPI inflation analyzer."""

from __future__ import annotations

from contracts.enums import SignalDirection

from economic.analyzers.base import Analyzer
from economic.models import EconomicSignal, EconomicSnapshot

__all__ = ["InflationAnalyzer"]

#: Low / target-like inflation ceiling (2%).
_LOW = 0.02
#: High inflation floor (4%).
_HIGH = 0.04


class InflationAnalyzer(Analyzer):
    """Classifies CPI inflation as low, moderate, or high."""

    @property
    def name(self) -> str:
        """Canonical analyzer identifier."""
        return "inflation"

    def analyze(self, snapshot: EconomicSnapshot) -> tuple[EconomicSignal, ...]:
        """Evaluate CPI inflation against fixed thresholds."""
        value = snapshot.cpi_inflation
        if value is None:
            return (
                EconomicSignal(
                    name="inflation",
                    direction=SignalDirection.NEUTRAL,
                    observation="Inflation Unavailable",
                    reasoning=(
                        "CPI inflation was not reported in the snapshot."
                    ),
                    value=None,
                ),
            )
        if value <= _LOW:
            return (
                EconomicSignal(
                    name="inflation",
                    direction=SignalDirection.BULLISH,
                    observation="Low Inflation",
                    reasoning=(
                        f"CPI inflation of {value:.1%} is at or below the "
                        f"{_LOW:.0%} low-inflation threshold."
                    ),
                    value=value,
                    threshold=_LOW,
                ),
            )
        if value <= _HIGH:
            return (
                EconomicSignal(
                    name="inflation",
                    direction=SignalDirection.NEUTRAL,
                    observation="Moderate Inflation",
                    reasoning=(
                        f"CPI inflation of {value:.1%} is between the "
                        f"{_LOW:.0%} and {_HIGH:.0%} thresholds."
                    ),
                    value=value,
                    threshold=_HIGH,
                ),
            )
        return (
            EconomicSignal(
                name="inflation",
                direction=SignalDirection.BEARISH,
                observation="High Inflation",
                reasoning=(
                    f"CPI inflation of {value:.1%} is above the "
                    f"{_HIGH:.0%} high-inflation threshold."
                ),
                value=value,
                threshold=_HIGH,
            ),
        )
