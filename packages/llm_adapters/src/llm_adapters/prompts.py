"""Structured prompt assembly — inject frozen deterministic research context."""

from __future__ import annotations

from typing import Any

from llm_adapters.deterministic_composer import ResearchPayload

_SYSTEM_CONSTRAINTS = (
    "You are a research explainability assistant for an investment terminal. "
    "You may explain, summarise, teach, and compare using ONLY the supplied "
    "deterministic research context. "
    "You must NEVER modify, override, or invent recommendations, scores, "
    "intrinsic values, committee decisions, or margin of safety figures. "
    "If information is missing, say it is unavailable. "
    "Live market data is read-only context and must not influence conclusions."
)


def build_prompt_parts(
    *,
    question: str,
    intent: str,
    research: ResearchPayload,
    market_context: dict[str, Any] | None = None,
) -> tuple[str, ...]:
    """Build cite-only structured prompt parts for LanguageModelRequest."""
    sections = [
        _SYSTEM_CONSTRAINTS,
        f"User question: {question.strip()}",
        f"Resolved intent: {intent}",
        f"Company: {research.company} ({research.ticker})",
        f"Exchange: {research.exchange or 'unknown'}",
        f"Recommendation (frozen): {research.recommendation}",
        f"Recommendation confidence (frozen): {research.recommendation_confidence}",
        f"Intrinsic value (frozen): {research.intrinsic_value}",
        f"Current price (frozen): {research.current_price}",
        f"Margin of safety (frozen): {research.margin_of_safety}",
        f"Business quality (frozen): {research.business_quality_label} "
        f"score={research.business_quality_score}",
        f"Committee decision (frozen): {research.committee_decision}",
        f"Committee confidence (frozen): {research.committee_confidence}",
        f"Economic moat (frozen): {research.economic_moat}",
        f"Management quality (frozen): {research.management_quality}",
        f"Financial strength (frozen): {research.financial_strength}",
        f"Strengths (frozen): {', '.join(research.strengths) or 'none'}",
        f"Weaknesses (frozen): {', '.join(research.weaknesses) or 'none'}",
        f"Risks (frozen): {', '.join(research.risks) or 'none'}",
    ]
    if market_context:
        sections.append(
            "Live market context (read-only): "
            + ", ".join(f"{k}={v}" for k, v in market_context.items())
        )
    sections.append(
        "Respond in clear prose. Reference frozen fields explicitly. "
        "Do not output JSON. Do not change any frozen values."
    )
    return tuple(sections)
