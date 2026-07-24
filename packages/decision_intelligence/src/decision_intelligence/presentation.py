"""Read-only presentation view derived from DecisionPack.

No recalculation, no analysis, no UI framework — sectioned projection only.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts import RecommendationAction
from decision_intelligence.models.enums import AssuranceLevel, GuidanceStance
from decision_intelligence.models.pack import DecisionPack

__all__ = [
    "ActionSection",
    "CautionSection",
    "CommitteeMemberView",
    "CommitteeSection",
    "DecisionPackView",
    "DecisionSection",
    "EvidenceSection",
    "RobustnessSection",
    "ValuationSection",
    "WatchSection",
    "WhySection",
    "present_decision_pack",
]


@dataclass(frozen=True, slots=True)
class DecisionSection:
    action: RecommendationAction
    conviction: float
    headline: str
    summary: str


@dataclass(frozen=True, slots=True)
class RobustnessSection:
    level: AssuranceLevel
    summary: str
    agreement_quality: str
    resilience: str


@dataclass(frozen=True, slots=True)
class ValuationSection:
    mos_available: bool
    mos_ratio: float | None
    intrinsic_mid: float | None
    intrinsic_low: float | None
    intrinsic_high: float | None
    currency: str | None
    confidence: str | None
    note: str


@dataclass(frozen=True, slots=True)
class CommitteeMemberView:
    source: str
    stance: str
    role: str
    rationale_excerpt: str


@dataclass(frozen=True, slots=True)
class CommitteeSection:
    members: tuple[CommitteeMemberView, ...]
    supporting: tuple[str, ...]
    dissenting: tuple[str, ...]
    neutral: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WhySection:
    strongest_evidence: tuple[str, ...]
    key_strengths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CautionSection:
    dissent: tuple[str, ...]
    fragilities: tuple[str, ...]
    invalidators: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ActionSection:
    stance: GuidanceStance
    rationale: str


@dataclass(frozen=True, slots=True)
class WatchSection:
    monitoring: tuple[str, ...]
    review_triggers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceSection:
    """Reference-only industry evidence citation — no observations."""

    attached: bool
    status: str | None
    availability: str
    bundle_version: str | None
    reference: str | None


@dataclass(frozen=True, slots=True)
class DecisionPackView:
    """Presentation-ready projection of a Decision Pack."""

    symbol: str
    decision: DecisionSection
    robustness: RobustnessSection
    valuation: ValuationSection
    committee: CommitteeSection
    why: WhySection
    caution: CautionSection
    action: ActionSection
    watch: WatchSection
    evidence: EvidenceSection


def present_decision_pack(pack: DecisionPack) -> DecisionPackView:
    """Project a DecisionPack into investor-facing sections (read-only)."""
    rec = pack.recommendation
    brief = pack.brief
    assurance = pack.assurance
    mos = rec.margin_of_safety
    summary = rec.valuation_summary

    if mos is None:
        mos_note = "Margin of Safety was not attached to this recommendation."
        mos_available = False
        mos_ratio = None
    elif mos.available:
        mos_note = "Margin of Safety is available (propagated, not recalculated)."
        mos_available = True
        mos_ratio = mos.ratio
    else:
        mos_note = "Margin of Safety was marked unavailable upstream."
        mos_available = False
        mos_ratio = None

    members = tuple(
        CommitteeMemberView(
            source=item.source,
            stance=item.stance,
            role=item.role,
            rationale_excerpt=item.rationale_excerpt,
        )
        for item in brief.attribution
    )
    supporting = tuple(m.source for m in members if m.role == "supporting")
    dissenting = tuple(m.source for m in members if m.role == "dissenting")
    neutral = tuple(m.source for m in members if m.role == "neutral")

    strongest = tuple(
        f"[{h.strength}] {h.claim} ({h.source_engine})"
        for h in brief.evidence_highlights
        if h.strength == "strong"
    )
    dissent_lines = tuple(
        f"{m.source}: {m.stance} — {m.rationale_excerpt}"
        for m in members
        if m.role == "dissenting"
    )
    triggers = tuple(
        f"[{t.urgency.value}] {t.condition}" for t in assurance.review_triggers
    )
    evidence_summary = pack.evidence_summary()

    return DecisionPackView(
        symbol=rec.instrument.symbol,
        decision=DecisionSection(
            action=rec.action,
            conviction=rec.conviction,
            headline=brief.headline,
            summary=brief.executive_summary,
        ),
        robustness=RobustnessSection(
            level=assurance.assurance_level,
            summary=assurance.robustness_summary,
            agreement_quality=assurance.agreement_quality.value,
            resilience=assurance.decision_resilience.value,
        ),
        valuation=ValuationSection(
            mos_available=mos_available,
            mos_ratio=mos_ratio,
            intrinsic_mid=None if summary is None else summary.intrinsic_mid,
            intrinsic_low=None if summary is None else summary.intrinsic_low,
            intrinsic_high=None if summary is None else summary.intrinsic_high,
            currency=None if summary is None else summary.currency,
            confidence=None if summary is None else summary.confidence,
            note=mos_note,
        ),
        committee=CommitteeSection(
            members=members,
            supporting=supporting,
            dissenting=dissenting,
            neutral=neutral,
        ),
        why=WhySection(
            strongest_evidence=strongest,
            key_strengths=assurance.key_strengths,
        ),
        caution=CautionSection(
            dissent=dissent_lines,
            fragilities=assurance.key_fragilities,
            invalidators=brief.invalidators,
        ),
        action=ActionSection(
            stance=assurance.investor_guidance.stance,
            rationale=assurance.investor_guidance.rationale,
        ),
        watch=WatchSection(
            monitoring=brief.monitoring_watchlist,
            review_triggers=triggers,
        ),
        evidence=EvidenceSection(
            attached=evidence_summary.attached,
            status=None
            if evidence_summary.status is None
            else evidence_summary.status.value,
            availability=evidence_summary.availability,
            bundle_version=evidence_summary.bundle_version,
            reference=evidence_summary.reference,
        ),
    )
