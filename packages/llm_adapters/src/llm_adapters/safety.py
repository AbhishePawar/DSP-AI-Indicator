"""Safety validation — LLM output must not override deterministic fields."""

from __future__ import annotations

import re

from llm_adapters.deterministic_composer import ResearchPayload

_OVERRIDE_PATTERNS = (
    re.compile(r"\b(?:new|updated|revised)\s+recommendation\b", re.I),
    re.compile(r"\b(?:intrinsic\s+value\s+(?:is|should\s+be))\s+\d", re.I),
    re.compile(r"\bcommittee\s+(?:now\s+)?(?:decides|recommends)\b", re.I),
    re.compile(r"\b(?:override|change|modify)\s+(?:the\s+)?(?:score|rating)\b", re.I),
)


def validate_llm_narrative(
    narrative: str,
    research: ResearchPayload,
) -> tuple[str, tuple[str, ...]]:
    """Return sanitized narrative and limitation warnings."""
    warnings: list[str] = []
    text = narrative.strip()
    if not text:
        return research_fallback_note(research), ("empty LLM narrative",)

    for pattern in _OVERRIDE_PATTERNS:
        if pattern.search(text):
            warnings.append(
                "LLM output contained override language — appended frozen disclaimer."
            )
            text = (
                f"{text}\n\n"
                "**Frozen deterministic values remain authoritative:** "
                f"Recommendation {research.recommendation}, "
                f"Committee {research.committee_decision}, "
                f"Margin of safety {research.margin_of_safety or 'unavailable'}."
            )
            break

    return text, tuple(warnings)


def research_fallback_note(research: ResearchPayload) -> str:
    return (
        f"Deterministic research for {research.company}: "
        f"recommendation {research.recommendation}, "
        f"committee {research.committee_decision}."
    )
