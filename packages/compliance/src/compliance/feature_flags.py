"""Product operating mode and UI capability feature flags (PR1.0).

Flags control **presentation and activation surfaces only**.
They do not alter valuation, recommendation, or workflow engines.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

__all__ = [
    "FeatureFlags",
    "load_feature_flags",
]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class FeatureFlags:
    """Immutable product mode flags.

    Phase 1 defaults: Research Mode on; recommendation / SEBI surfaces off.
    """

    research_mode: bool = True
    recommendation_mode: bool = False
    sebi_mode: bool = False
    show_target_price: bool = False
    show_buy_sell: bool = False
    show_model_portfolio: bool = False
    show_research_alerts: bool = False

    def allow_action_labels(self) -> bool:
        """True when BUY/SELL/HOLD may appear in UI."""
        return (
            self.recommendation_mode
            and self.sebi_mode
            and self.show_buy_sell
        )

    def allow_official_target_price(self) -> bool:
        """True when official Target Price labeling may appear."""
        return (
            self.recommendation_mode
            and self.sebi_mode
            and self.show_target_price
        )

    def is_research_only(self) -> bool:
        return self.research_mode and not self.sebi_mode

    def validate(self) -> tuple[str, ...]:
        """Return soft policy warnings (never raises — architecture guard)."""
        warnings: list[str] = []
        if self.sebi_mode and not self.recommendation_mode:
            warnings.append(
                "SEBI_MODE=true without RECOMMENDATION_MODE=true is inconsistent"
            )
        if self.show_buy_sell and not self.sebi_mode:
            warnings.append(
                "ShowBuySell requires SEBI_MODE for official recommendation labels"
            )
        if self.show_target_price and not self.sebi_mode:
            warnings.append(
                "ShowTargetPrice requires SEBI_MODE for official target labeling"
            )
        if not self.research_mode and not self.sebi_mode:
            warnings.append("At least one of RESEARCH_MODE or SEBI_MODE should be on")
        return tuple(warnings)


def load_feature_flags() -> FeatureFlags:
    """Load flags from environment (Phase 1 defaults when unset)."""
    return FeatureFlags(
        research_mode=_env_bool("RESEARCH_MODE", True),
        recommendation_mode=_env_bool("RECOMMENDATION_MODE", False),
        sebi_mode=_env_bool("SEBI_MODE", False),
        show_target_price=_env_bool("SHOW_TARGET_PRICE", False),
        show_buy_sell=_env_bool("SHOW_BUY_SELL", False),
        show_model_portfolio=_env_bool("SHOW_MODEL_PORTFOLIO", False),
        show_research_alerts=_env_bool("SHOW_RESEARCH_ALERTS", False),
    )
