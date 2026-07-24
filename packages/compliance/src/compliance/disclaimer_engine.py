"""Contextual disclaimer selection — architecture only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from compliance.feature_flags import FeatureFlags

__all__ = ["Disclaimer", "DisclaimerEnginePort", "default_research_disclaimer"]


@dataclass(frozen=True, slots=True)
class Disclaimer:
    disclaimer_id: str
    text: str
    severity: str = "standard"


@runtime_checkable
class DisclaimerEnginePort(Protocol):
    def for_flags(self, flags: FeatureFlags) -> tuple[Disclaimer, ...]: ...


def default_research_disclaimer() -> Disclaimer:
    """Phase 1 default — research / education posture, not a tip."""
    return Disclaimer(
        disclaimer_id="research_mode_v1",
        text=(
            "DSP AI Indicator provides investment research and decision support. "
            "In Research Mode it does not issue Buy, Sell, or Hold recommendations. "
            "Past analysis is not a guarantee of future results. "
            "Users remain responsible for their own investment decisions."
        ),
        severity="standard",
    )
