"""Presentation terminology — Research Mode vs SEBI Mode (PR1.0).

Maps engine/domain action tokens to **user-facing labels**.
Does not mutate recommendation or decision engines.
"""

from __future__ import annotations

from enum import StrEnum

from compliance.feature_flags import FeatureFlags

__all__ = [
    "ResearchLabel",
    "FIELD_LABELS_RESEARCH",
    "FIELD_LABELS_SEBI",
    "present_action",
    "present_field_label",
]


class ResearchLabel(StrEnum):
    """Neutral DSP View labels used in Research Mode."""

    ATTRACTIVE = "Attractive"
    CAUTION = "Caution"
    FAIRLY_VALUED = "Fairly Valued"
    REDUCE_EXPOSURE = "Reduce Exposure"
    WATCH = "Watch Closely"
    INSUFFICIENT_EVIDENCE = "Insufficient Evidence"
    UNKNOWN = "Unclassified"


# Canonical engine / API tokens → Research Mode DSP View
_ACTION_TO_RESEARCH: dict[str, ResearchLabel] = {
    "strong_buy": ResearchLabel.ATTRACTIVE,
    "buy": ResearchLabel.ATTRACTIVE,
    "hold": ResearchLabel.FAIRLY_VALUED,
    "neutral": ResearchLabel.FAIRLY_VALUED,
    "reduce": ResearchLabel.REDUCE_EXPOSURE,
    "sell": ResearchLabel.CAUTION,
    "strong_sell": ResearchLabel.CAUTION,
    "watch": ResearchLabel.WATCH,
    "insufficient_evidence": ResearchLabel.INSUFFICIENT_EVIDENCE,
}

# SEBI / recommendation mode retains conventional labels (architecture only)
_ACTION_TO_SEBI: dict[str, str] = {
    "strong_buy": "Strong Buy",
    "buy": "Buy",
    "hold": "Hold",
    "neutral": "Hold",
    "reduce": "Reduce",
    "sell": "Sell",
    "strong_sell": "Strong Sell",
    "watch": "Watch",
    "insufficient_evidence": "Insufficient Evidence",
}

FIELD_LABELS_RESEARCH: dict[str, str] = {
    "target_price": "Estimated Intrinsic Value Range",
    "recommendation": "Research Conclusion",
    "stock_recommendation": "Investment Assessment",
    "action": "DSP View",
    "official_target_price": "Estimated Intrinsic Value Range",
}

FIELD_LABELS_SEBI: dict[str, str] = {
    "target_price": "Official Target Price",
    "recommendation": "Recommendation",
    "stock_recommendation": "Stock Recommendation",
    "action": "Recommendation",
    "official_target_price": "Official Target Price",
}


def present_action(token: str, flags: FeatureFlags | None = None) -> str:
    """Return user-facing action / posture label for ``token``.

    Parameters
    ----------
    token:
        Engine or API action string (e.g. ``buy``, ``STRONG_BUY``).
    flags:
        When ``allow_action_labels()`` is true, SEBI wording is used.
        Otherwise Research Mode neutral DSP View labels are used.
    """
    key = token.strip().lower().replace(" ", "_").replace("-", "_")
    active = flags or FeatureFlags()
    if active.allow_action_labels():
        return _ACTION_TO_SEBI.get(key, token)
    label = _ACTION_TO_RESEARCH.get(key, ResearchLabel.UNKNOWN)
    return str(label)


def present_field_label(field_key: str, flags: FeatureFlags | None = None) -> str:
    """Return user-facing field title for a conceptual field key."""
    key = field_key.strip().lower()
    active = flags or FeatureFlags()
    table = (
        FIELD_LABELS_SEBI
        if active.allow_official_target_price() or active.allow_action_labels()
        else FIELD_LABELS_RESEARCH
    )
    if active.allow_official_target_price() and key in {
        "target_price",
        "official_target_price",
    }:
        return FIELD_LABELS_SEBI["official_target_price"]
    if not active.allow_action_labels() and key in FIELD_LABELS_RESEARCH:
        return FIELD_LABELS_RESEARCH[key]
    return table.get(key, field_key)
