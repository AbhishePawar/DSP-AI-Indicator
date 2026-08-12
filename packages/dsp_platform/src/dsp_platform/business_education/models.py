"""Models for educational Business & Buffett analysis (read-only)."""

from __future__ import annotations

from enum import Enum
from typing import Any

UNAVAILABLE_MESSAGE = "Data unavailable."
BUSINESS_EDUCATION_SCHEMA_VERSION = "1.0.0"

SECTION_ORDER: tuple[str, ...] = (
    "the_business_simply",
    "how_the_economics_work",
    "the_real_strengths",
    "the_real_weaknesses",
    "financial_health",
    "key_risks_to_understand",
    "the_buffett_checklist",
    "management_and_capital_allocation",
    "the_behavioral_lens",
    "what_would_change_the_thesis",
    "data_quality_and_uncertainty",
    "educational_conclusion",
)

SECTION_TITLES: dict[str, str] = {
    "the_business_simply": "The Business, Simply",
    "how_the_economics_work": "How the Economics Work",
    "the_real_strengths": "The Real Strengths",
    "the_real_weaknesses": "The Real Weaknesses",
    "financial_health": "Financial Health",
    "key_risks_to_understand": "Key Risks to Understand",
    "the_buffett_checklist": "The Buffett Checklist",
    "management_and_capital_allocation": "Management & Capital Allocation",
    "the_behavioral_lens": "The Behavioral Lens",
    "what_would_change_the_thesis": "What Would Change the Thesis?",
    "data_quality_and_uncertainty": "Data Quality & Uncertainty",
    "educational_conclusion": "Educational Conclusion",
}


class ClaimKind(str, Enum):
    FACT = "FACT"
    CALCULATED_METRIC = "CALCULATED_METRIC"
    INTERPRETATION = "INTERPRETATION"
    MANAGEMENT_CLAIM = "MANAGEMENT_CLAIM"
    UNAVAILABLE = "UNAVAILABLE"


# Educational conclusion must not emit investment verdict language.
PROHIBITED_VERDICT_TOKENS: frozenset[str] = frozenset(
    {
        "buy",
        "sell",
        "hold",
        "strong buy",
        "strong sell",
        "price target",
        "target price",
        "expected return",
        "future price",
    }
)


def claim(
    text: str,
    *,
    kind: ClaimKind,
    source: str | None = None,
    available: bool = True,
) -> dict[str, Any]:
    return {
        "text": text if available else UNAVAILABLE_MESSAGE,
        "kind": kind.value,
        "source": source,
        "available": available and bool(text and text.strip()),
    }
