"""Comparable Decision Pack summaries — read-only, no ranking."""

from __future__ import annotations

from dataclasses import dataclass

from contracts import Instrument, RecommendationAction
from decision_intelligence import (
    AssuranceLevel,
    DecisionPack,
    GuidanceStance,
)

__all__ = ["ComparableDecisionSummary", "summarize_decision_pack"]


@dataclass(frozen=True, slots=True)
class ComparableDecisionSummary:
    """Normalized single-name snapshot for multi-stock views.

    Does **not** invent a composite score or claim relative superiority.
    """

    instrument: Instrument
    action: RecommendationAction
    conviction: float
    assurance_level: AssuranceLevel
    guidance: GuidanceStance
    mos_available: bool
    mos_ratio: float | None
    intrinsic_mid: float | None
    intrinsic_currency: str | None
    agreement_quality: str
    supporting_sources: tuple[str, ...]
    dissenting_sources: tuple[str, ...]
    primary_fragility: str | None
    headline: str


def summarize_decision_pack(pack: DecisionPack) -> ComparableDecisionSummary:
    """Project a DecisionPack into a comparable summary (no recalculation)."""
    rec = pack.recommendation
    brief = pack.brief
    assurance = pack.assurance
    mos = rec.margin_of_safety
    summary = rec.valuation_summary

    supporting = tuple(
        a.source for a in brief.attribution if a.role == "supporting"
    )
    dissenting = tuple(
        a.source for a in brief.attribution if a.role == "dissenting"
    )
    fragility = (
        assurance.key_fragilities[0] if assurance.key_fragilities else None
    )

    if mos is None:
        mos_available = False
        mos_ratio = None
    else:
        mos_available = mos.available
        mos_ratio = mos.ratio if mos.available else None

    return ComparableDecisionSummary(
        instrument=rec.instrument,
        action=rec.action,
        conviction=rec.conviction,
        assurance_level=assurance.assurance_level,
        guidance=assurance.investor_guidance.stance,
        mos_available=mos_available,
        mos_ratio=mos_ratio,
        intrinsic_mid=None if summary is None else summary.intrinsic_mid,
        intrinsic_currency=None if summary is None else summary.currency,
        agreement_quality=assurance.agreement_quality.value,
        supporting_sources=supporting,
        dissenting_sources=dissenting,
        primary_fragility=fragility,
        headline=brief.headline,
    )
