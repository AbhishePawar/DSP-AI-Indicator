"""Consensus and minority opinion assembly (EPIC-A005)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.institutional_committee.models import AgentReview, freeze_mapping

__all__ = ["build_consensus", "build_minority_opinions", "build_committee_summary"]


def build_consensus(reviews: tuple[AgentReview, ...]) -> Mapping[str, Any]:
    """Majority stance among agents with usable reviews (deterministic)."""
    counts: dict[str, int] = {"supportive": 0, "cautionary": 0, "unavailable": 0}
    for review in reviews:
        counts[review.stance] = counts.get(review.stance, 0) + 1

    usable = [r for r in reviews if r.stance != "unavailable"]
    if not usable:
        stance = "unavailable"
    else:
        # Prefer cautionary on ties (conservative institutional posture)
        usable_counts = {
            "supportive": sum(1 for r in usable if r.stance == "supportive"),
            "cautionary": sum(1 for r in usable if r.stance == "cautionary"),
        }
        if usable_counts["cautionary"] >= usable_counts["supportive"]:
            stance = "cautionary"
        else:
            stance = "supportive"

    confidence_rank = {"unavailable": 0, "low": 1, "medium": 2, "high": 3}
    if usable:
        # Committee confidence = minimum among usable agents (conservative, not a score)
        conf = min(usable, key=lambda r: confidence_rank.get(r.confidence, 0)).confidence
    else:
        conf = "unavailable"

    agreeing = [r.agent_id for r in reviews if r.stance == stance]
    return freeze_mapping(
        {
            "stance": stance,
            "confidence": conf,
            "counts": counts,
            "agreeing_agents": agreeing,
            "usable_agent_count": len(usable),
            "total_agent_count": len(reviews),
        }
    ) or freeze_mapping({})


def build_minority_opinions(
    reviews: tuple[AgentReview, ...],
    consensus: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    stance = str(consensus.get("stance") or "")
    minorities: list[Mapping[str, Any]] = []
    for review in reviews:
        if review.stance == stance:
            continue
        if review.stance == "unavailable" and stance == "unavailable":
            continue
        minorities.append(
            freeze_mapping(
                {
                    "agent_id": review.agent_id,
                    "agent_name": review.agent_name,
                    "stance": review.stance,
                    "confidence": review.confidence,
                    "summary": review.summary,
                    "findings": list(review.findings),
                }
            )
            or freeze_mapping({})
        )
    minorities.sort(key=lambda m: str(m.get("agent_id") or ""))
    return tuple(minorities)


def build_committee_summary(
    *,
    subject: str,
    reviews: tuple[AgentReview, ...],
    consensus: Mapping[str, Any],
    minority_opinions: tuple[Mapping[str, Any], ...],
) -> Mapping[str, Any]:
    return freeze_mapping(
        {
            "subject": subject,
            "consensus_stance": consensus.get("stance"),
            "consensus_confidence": consensus.get("confidence"),
            "agent_count": len(reviews),
            "minority_count": len(minority_opinions),
            "reviews_by_stance": {
                "supportive": [
                    r.agent_id for r in reviews if r.stance == "supportive"
                ],
                "cautionary": [
                    r.agent_id for r in reviews if r.stance == "cautionary"
                ],
                "unavailable": [
                    r.agent_id for r in reviews if r.stance == "unavailable"
                ],
            },
            "note": (
                "Committee explains cited evidence only; "
                "no recommendations or new research."
            ),
        }
    ) or freeze_mapping({})
