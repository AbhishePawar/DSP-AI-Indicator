"""Interest-rate / policy-rate analyzer."""

from __future__ import annotations

from contracts.enums import SignalDirection

from economic.analyzers.base import Analyzer
from economic.models import EconomicSignal, EconomicSnapshot

__all__ = ["InterestRateAnalyzer"]

#: Rapid hike threshold (75 bps since prior observation).
_RAPID_HIKE = 0.0075
#: Meaningful easing threshold (-25 bps).
_EASING = -0.0025
#: Accommodative rate ceiling (3%).
_ACCOMMODATIVE = 0.03
#: Restrictive rate floor (5.5%).
_RESTRICTIVE = 0.055


class InterestRateAnalyzer(Analyzer):
    """Classifies policy rates and recent rate changes.

    Rapid hikes take precedence over the absolute rate level when
    ``interest_rate_change`` is available, matching the mission example
    "High Inflation + Rapid Rate Hikes → Bearish."
    """

    @property
    def name(self) -> str:
        """Canonical analyzer identifier."""
        return "interest_rate"

    def analyze(self, snapshot: EconomicSnapshot) -> tuple[EconomicSignal, ...]:
        """Evaluate interest-rate level and recent change."""
        change = snapshot.interest_rate_change
        if change is not None and change >= _RAPID_HIKE:
            return (
                EconomicSignal(
                    name="interest_rate",
                    direction=SignalDirection.BEARISH,
                    observation="Rapid Rate Hikes",
                    reasoning=(
                        f"Interest-rate change of {change:.2%} meets or "
                        f"exceeds the {_RAPID_HIKE:.2%} rapid-hike "
                        "threshold."
                    ),
                    value=change,
                    threshold=_RAPID_HIKE,
                ),
            )
        if change is not None and change <= _EASING:
            return (
                EconomicSignal(
                    name="interest_rate",
                    direction=SignalDirection.BULLISH,
                    observation="Easing Rates",
                    reasoning=(
                        f"Interest-rate change of {change:.2%} is at or "
                        f"below the {_EASING:.2%} easing threshold."
                    ),
                    value=change,
                    threshold=_EASING,
                ),
            )

        value = snapshot.interest_rate
        if value is None:
            return (
                EconomicSignal(
                    name="interest_rate",
                    direction=SignalDirection.NEUTRAL,
                    observation="Interest Rate Unavailable",
                    reasoning=(
                        "Interest rate was not reported in the snapshot."
                    ),
                    value=None,
                ),
            )
        if value <= _ACCOMMODATIVE:
            return (
                EconomicSignal(
                    name="interest_rate",
                    direction=SignalDirection.BULLISH,
                    observation="Accommodative Rates",
                    reasoning=(
                        f"Interest rate of {value:.1%} is at or below the "
                        f"{_ACCOMMODATIVE:.1%} accommodative threshold."
                    ),
                    value=value,
                    threshold=_ACCOMMODATIVE,
                ),
            )
        if value <= _RESTRICTIVE:
            return (
                EconomicSignal(
                    name="interest_rate",
                    direction=SignalDirection.NEUTRAL,
                    observation="Stable Rates",
                    reasoning=(
                        f"Interest rate of {value:.1%} is between the "
                        f"{_ACCOMMODATIVE:.1%} and {_RESTRICTIVE:.1%} "
                        "thresholds (stable / neutral policy stance)."
                    ),
                    value=value,
                    threshold=_RESTRICTIVE,
                ),
            )
        return (
            EconomicSignal(
                name="interest_rate",
                direction=SignalDirection.BEARISH,
                observation="Restrictive Rates",
                reasoning=(
                    f"Interest rate of {value:.1%} is above the "
                    f"{_RESTRICTIVE:.1%} restrictive threshold."
                ),
                value=value,
                threshold=_RESTRICTIVE,
            ),
        )
