"""Deterministic copilot answer composer — server-side fallback, no LLM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ResearchPayload:
    company: str
    ticker: str
    exchange: str | None
    recommendation: str
    recommendation_confidence: str | None
    intrinsic_value: str | None
    current_price: str | None
    margin_of_safety: str | None
    business_quality_label: str
    business_quality_score: str | None
    committee_decision: str
    committee_confidence: str | None
    economic_moat: str
    management_quality: str
    financial_strength: str
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    risks: tuple[str, ...]
    has_session: bool


@dataclass(frozen=True, slots=True)
class DeterministicAnswer:
    content: str
    citations: tuple[str, ...]
    intent: str
    unavailable: bool


_UNAVAILABLE = (
    "I can only explain from an existing research session. "
    "Run analysis first — I will not invent numbers or conclusions."
)


def _stage_label(stages: list[dict[str, Any]] | None, stage: str) -> str:
    if not stages:
        return "Unavailable"
    for item in stages:
        if item.get("stage") == stage and item.get("has_result"):
            return str(item.get("label") or item.get("decision") or "Available")
    return "Unavailable"


def _pct(value: float | None) -> str | None:
    if value is None:
        return None
    return f"{value * 100:.1f}%"


def extract_research_payload(
    request: dict[str, Any] | None,
    response: dict[str, Any] | None,
) -> ResearchPayload:
    """Map analyse transport payloads into a research context bundle."""
    if not request or not response or not response.get("ok"):
        return ResearchPayload(
            company="Unknown",
            ticker="",
            exchange=None,
            recommendation="Unavailable",
            recommendation_confidence=None,
            intrinsic_value=None,
            current_price=None,
            margin_of_safety=None,
            business_quality_label="Unavailable",
            business_quality_score=None,
            committee_decision="Unavailable",
            committee_confidence=None,
            economic_moat="Unavailable",
            management_quality="Unavailable",
            financial_strength="Unavailable",
            strengths=(),
            weaknesses=(),
            risks=(),
            has_session=False,
        )

    payload = response.get("payload") or {}
    rec = payload.get("recommendation_summary") or {}
    committee = payload.get("committee_summary") or {}
    stages = payload.get("stage_summaries") or []
    strengths = tuple(
        str(s.get("label"))
        for s in stages
        if s.get("has_result") and s.get("label")
    )

    intrinsic = request.get("intrinsic_value_per_share")
    if intrinsic is None:
        signals = request.get("valuation_signals") or {}
        intrinsic = signals.get("intrinsic_value_per_share")
    current = request.get("current_market_price")
    if current is None:
        signals = request.get("valuation_signals") or {}
        current = signals.get("current_market_price")

    bq = _stage_label(stages, "business_quality_aggregator")

    return ResearchPayload(
        company=str(request.get("company") or request.get("ticker") or "Unknown"),
        ticker=str(request.get("ticker") or ""),
        exchange=request.get("exchange"),
        recommendation=str(rec.get("decision") or "Unavailable"),
        recommendation_confidence=_pct(rec.get("confidence")),
        intrinsic_value=str(intrinsic) if intrinsic is not None else None,
        current_price=str(current) if current is not None else None,
        margin_of_safety=_pct(rec.get("margin_of_safety")),
        business_quality_label=bq,
        business_quality_score=None,
        committee_decision=str(committee.get("decision") or "Unavailable"),
        committee_confidence=_pct(committee.get("confidence")),
        economic_moat=_stage_label(stages, "economic_moat"),
        management_quality=_stage_label(stages, "management_quality"),
        financial_strength=_stage_label(stages, "financial_strength"),
        strengths=strengths[:5],
        weaknesses=(),
        risks=(),
        has_session=True,
    )


def compose_deterministic_answer(
    *,
    question_id: str,
    freeform: str | None,
    research: ResearchPayload,
    last_intent: str | None = None,
) -> DeterministicAnswer:
    """Compose a deterministic explainability answer from frozen research fields."""
    if not research.has_session:
        return DeterministicAnswer(
            content=_UNAVAILABLE,
            citations=(),
            intent="unknown",
            unavailable=True,
        )

    intent = _resolve_intent(question_id, freeform, last_intent)
    citations = _citations_for_intent(intent)

    if intent == "explain_recommendation":
        content = (
            f"The deterministic recommendation for {research.company} "
            f"({research.ticker}) is **{research.recommendation}** "
            f"with confidence {research.recommendation_confidence or 'unavailable'}. "
            f"Margin of safety: {research.margin_of_safety or 'unavailable'}. "
            "These values come from the frozen /api/v1/analyse pipeline."
        )
    elif intent == "explain_valuation":
        content = (
            f"Valuation context for {research.company}: intrinsic value "
            f"{research.intrinsic_value or 'unavailable'}, current price "
            f"{research.current_price or 'unavailable'}, margin of safety "
            f"{research.margin_of_safety or 'unavailable'}. "
            "I explain only — I do not recalculate valuation."
        )
    elif intent == "explain_moat":
        content = (
            f"Economic moat assessment (frozen): {research.economic_moat}. "
            "See the Economic Moat research section for evidence."
        )
    elif intent == "explain_committee":
        content = (
            f"Investment committee decision (frozen): {research.committee_decision} "
            f"with confidence {research.committee_confidence or 'unavailable'}."
        )
    elif intent == "summarise_strengths":
        joined = ", ".join(research.strengths) if research.strengths else "none reported"
        content = f"Reported strengths from stage summaries: {joined}."
    elif intent == "compare_companies":
        content = (
            f"{_UNAVAILABLE} To compare companies, load research sessions for "
            "at least two tickers."
        )
        return DeterministicAnswer(
            content=content,
            citations=(),
            intent=intent,
            unavailable=True,
        )
    else:
        content = (
            f"I can explain deterministic research fields for {research.company}. "
            f"Recommendation: {research.recommendation}. "
            f"Committee: {research.committee_decision}. "
            "Ask about valuation, moat, committee, or strengths."
        )

    return DeterministicAnswer(
        content=content,
        citations=citations,
        intent=intent,
        unavailable=False,
    )


def _resolve_intent(
    question_id: str,
    freeform: str | None,
    last_intent: str | None,
) -> str:
    mapping = {
        "why_buy": "explain_recommendation",
        "explain_valuation": "explain_valuation",
        "explain_moat": "explain_moat",
        "explain_committee": "explain_committee",
        "summarise_strengths": "summarise_strengths",
        "compare_companies": "compare_companies",
    }
    if question_id != "freeform":
        return mapping.get(question_id, "unknown")
    text = (freeform or "").lower()
    if "compare" in text:
        return "compare_companies"
    if "moat" in text:
        return "explain_moat"
    if "committee" in text:
        return "explain_committee"
    if "valuation" in text or "intrinsic" in text:
        return "explain_valuation"
    if "strength" in text:
        return "summarise_strengths"
    if "recommend" in text or "buy" in text or "sell" in text:
        return "explain_recommendation"
    if "more" in text and last_intent:
        return last_intent
    return "unknown"


def _citations_for_intent(intent: str) -> tuple[str, ...]:
    table = {
        "explain_recommendation": ("Recommendation", "Valuation"),
        "explain_valuation": ("Valuation",),
        "explain_moat": ("Economic Moat",),
        "explain_committee": ("Investment Committee",),
        "summarise_strengths": ("Overview",),
    }
    return table.get(intent, ("Overview",))
