"""UX metric presentation schema — every metric answers the design questions."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["MetricPresentation", "metric_card_fields"]


@dataclass(frozen=True, slots=True)
class MetricPresentation:
    """Canonical metric card shape for Research Mode UI.

    Answers: What is happening? Why? Why care? What next?
    """

    title: str
    rating: str
    actual_value: str
    plain_english_explanation: str
    why_it_matters: str
    investor_takeaway: str


def metric_card_fields() -> tuple[str, ...]:
    """Ordered field names for UI / documentation generators."""
    return (
        "title",
        "rating",
        "actual_value",
        "plain_english_explanation",
        "why_it_matters",
        "investor_takeaway",
    )
