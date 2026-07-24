"""Deterministic Decision Assurance framework and guidance tables."""

from __future__ import annotations

from ai_committee import CommitteeReport, Decision
from contracts import Recommendation, RecommendationAction

from decision_intelligence.models.assurance import (
    AssuranceAssessment,
    ConfidenceDriver,
    InvestorGuidance,
    ReviewTrigger,
)
from decision_intelligence.models.enums import (
    AgreementQuality,
    AssuranceLevel,
    AssumptionRiskLevel,
    DecisionResilience,
    DriverDirection,
    EvidenceConsistency,
    GuidanceStance,
    InvalidationSensitivity,
    ReviewUrgency,
)

__all__ = ["build_assurance_assessment"]

_ACTION_TO_DECISION: dict[RecommendationAction, Decision] = {
    RecommendationAction.BUY: Decision.BUY,
    RecommendationAction.STRONG_BUY: Decision.BUY,
    RecommendationAction.HOLD: Decision.HOLD,
    RecommendationAction.SELL: Decision.SELL,
    RecommendationAction.STRONG_SELL: Decision.SELL,
}


def build_assurance_assessment(
    report: CommitteeReport,
    recommendation: Recommendation,
) -> AssuranceAssessment:
    """Assess recommendation robustness from deliberation structure only."""
    final = _final_decision(report, recommendation)
    votes = report.votes
    n = len(votes)
    agreeing = [v for v in votes if v.recommendation is final]
    hard_dissent: list = []
    soft_dissent: list = []
    for v in votes:
        if v.recommendation is final:
            continue
        if final in {Decision.BUY, Decision.SELL} and v.recommendation in {
            Decision.BUY,
            Decision.SELL,
        }:
            hard_dissent.append(v)
        elif final in {Decision.BUY, Decision.SELL} and v.recommendation is Decision.HOLD:
            soft_dissent.append(v)
        elif final is Decision.HOLD and v.recommendation in {
            Decision.BUY,
            Decision.SELL,
        }:
            hard_dissent.append(v)
        else:
            soft_dissent.append(v)

    agree_frac = len(agreeing) / n if n else 0.0
    agreement = _agreement_quality(
        report=report,
        agree_frac=agree_frac,
        hard_dissent=len(hard_dissent),
    )
    single_dep, dominant = _single_engine_dependence(agreeing, final)
    mos_available = bool(
        recommendation.margin_of_safety is not None
        and recommendation.margin_of_safety.available
    )
    valuation_supports = any(v.source == "valuation" for v in agreeing)
    evidence_consistency = _evidence_consistency(
        recommendation=recommendation,
        agreeing=agreeing,
    )
    assumption_risk = _assumption_risk(
        recommendation=recommendation,
        agreeing=agreeing,
        single_dep=single_dep,
        mos_available=mos_available,
    )
    sensitivity = _invalidation_sensitivity(n, len(agreeing), len(hard_dissent))
    level = _assurance_level(
        agreement=agreement,
        hard_dissent=len(hard_dissent),
        single_dep=single_dep,
        evidence_consistency=evidence_consistency,
        assumption_risk=assumption_risk,
        final=final,
        valuation_supports=valuation_supports,
        mos_available=mos_available,
    )
    resilience = _resilience(level)
    drivers = _drivers(
        agreement=agreement,
        agree_frac=agree_frac,
        hard_dissent=hard_dissent,
        soft_dissent=soft_dissent,
        single_dep=single_dep,
        dominant=dominant,
        mos_available=mos_available,
        evidence_consistency=evidence_consistency,
        assumption_risk=assumption_risk,
    )
    strengths = _strengths(drivers, agreement, mos_available, agreeing)
    fragilities = _fragilities(
        drivers, single_dep, hard_dissent, soft_dissent, assumption_risk
    )
    triggers = _review_triggers(
        recommendation=recommendation,
        hard_dissent=hard_dissent,
        soft_dissent=soft_dissent,
        mos_available=mos_available,
        agreeing=agreeing,
    )
    guidance = _guidance(
        level=level,
        recommendation=recommendation,
        agreement=agreement,
        single_dep=single_dep,
        mos_available=mos_available,
        hard_dissent=hard_dissent,
        agreeing=agreeing,
    )
    summary = _robustness_summary(
        level=level,
        agreement=agreement,
        resilience=resilience,
        single_dep=single_dep,
        dominant=dominant,
    )

    return AssuranceAssessment(
        instrument=recommendation.instrument,
        action=recommendation.action,
        conviction=recommendation.conviction,
        assurance_level=level,
        robustness_summary=summary,
        agreement_quality=agreement,
        key_strengths=strengths,
        key_fragilities=fragilities,
        confidence_drivers=drivers,
        single_engine_dependence=single_dep,
        dominant_supporting_source=dominant,
        assumption_risk=assumption_risk,
        evidence_consistency=evidence_consistency,
        decision_resilience=resilience,
        invalidation_sensitivity=sensitivity,
        review_triggers=triggers,
        investor_guidance=guidance,
        generated_at=recommendation.generated_at,
    )


def _final_decision(
    report: CommitteeReport, recommendation: Recommendation
) -> Decision:
    decision = report.decision.decision
    if decision is Decision.NEUTRAL:
        return Decision.HOLD
    return _ACTION_TO_DECISION.get(recommendation.action, decision)


def _agreement_quality(
    *,
    report: CommitteeReport,
    agree_frac: float,
    hard_dissent: int,
) -> AgreementQuality:
    if report.decision.decision is Decision.NEUTRAL:
        return AgreementQuality.CONFLICT
    if hard_dissent > 0 and agree_frac < 0.75:
        if agree_frac <= 0.5:
            return AgreementQuality.CONFLICT
        return AgreementQuality.NARROW
    if agree_frac >= 1.0:
        return AgreementQuality.UNANIMOUS
    if agree_frac >= 0.75:
        return AgreementQuality.STRONG_MAJORITY
    if agree_frac > 0.5:
        return AgreementQuality.MAJORITY
    if agree_frac == 0.5:
        return AgreementQuality.NARROW
    # Minority directional win with only soft dissent is narrow, not conflict.
    if hard_dissent == 0:
        return AgreementQuality.NARROW
    return AgreementQuality.CONFLICT


def _single_engine_dependence(
    agreeing: list,
    final: Decision,
) -> tuple[bool, str | None]:
    if final is Decision.HOLD:
        return False, None
    directional = [
        v for v in agreeing if v.recommendation in {Decision.BUY, Decision.SELL}
    ]
    if len(directional) == 1:
        return True, directional[0].source
    if len(agreeing) == 1 and agreeing[0].recommendation is final:
        return True, agreeing[0].source
    return False, None


def _evidence_consistency(
    *,
    recommendation: Recommendation,
    agreeing: list,
) -> EvidenceConsistency:
    """Judge evidence breadth from analytical domains, not provenance tags.

    Committee opinions typically tag evidence as ``AI_COMMITTEE``; counting
    ``EngineSource`` therefore understates multi-domain support. Prefer the
    count of agreeing members that contributed evidence.
    """
    domains_with_evidence = {
        vote.source for vote in agreeing if vote.opinion.evidence
    }
    if len(domains_with_evidence) >= 2:
        return EvidenceConsistency.ALIGNED
    supporting = recommendation.supporting_evidence
    if not supporting:
        return EvidenceConsistency.THIN
    if len(supporting) >= 2 and len(domains_with_evidence) == 1:
        return EvidenceConsistency.MIXED
    if len(domains_with_evidence) == 1:
        return EvidenceConsistency.THIN
    return EvidenceConsistency.THIN


def _assumption_risk(
    *,
    recommendation: Recommendation,
    agreeing: list,
    single_dep: bool,
    mos_available: bool,
) -> AssumptionRiskLevel:
    valuation_supported = any(v.source == "valuation" for v in agreeing)
    if single_dep and valuation_supported and not mos_available:
        return AssumptionRiskLevel.HIGH
    if single_dep:
        return AssumptionRiskLevel.HIGH
    if valuation_supported and not mos_available:
        return AssumptionRiskLevel.ELEVATED
    if recommendation.conviction < 0.6:
        return AssumptionRiskLevel.ELEVATED
    return AssumptionRiskLevel.LOW


def _invalidation_sensitivity(
    n: int, agreeing: int, hard_dissent: int
) -> InvalidationSensitivity:
    if n <= 1:
        return InvalidationSensitivity.HIGH
    margin = agreeing - (n - agreeing)
    if hard_dissent > 0 or margin <= 1:
        return InvalidationSensitivity.HIGH
    if margin == 2:
        return InvalidationSensitivity.MEDIUM
    return InvalidationSensitivity.LOW


def _assurance_level(
    *,
    agreement: AgreementQuality,
    hard_dissent: int,
    single_dep: bool,
    evidence_consistency: EvidenceConsistency,
    assumption_risk: AssumptionRiskLevel,
    final: Decision,
    valuation_supports: bool,
    mos_available: bool,
) -> AssuranceLevel:
    if agreement is AgreementQuality.CONFLICT:
        return AssuranceLevel.LOW

    score = 3  # 3=HIGH … 0=LOW
    if agreement is AgreementQuality.UNANIMOUS:
        score = 3
    elif agreement is AgreementQuality.STRONG_MAJORITY:
        score = 3
    elif agreement is AgreementQuality.MAJORITY:
        score = 2
    elif agreement is AgreementQuality.NARROW:
        score = 1
    else:
        score = 0

    if hard_dissent > 0:
        score -= 1
    if single_dep:
        score -= 1
    if evidence_consistency is EvidenceConsistency.THIN:
        score -= 1
    if assumption_risk is AssumptionRiskLevel.HIGH:
        score -= 1
    # Valuation-supported directional calls without usable MoS are less assured.
    if (
        valuation_supports
        and not mos_available
        and final in {Decision.BUY, Decision.SELL}
    ):
        score -= 1
    if final is Decision.HOLD and hard_dissent > 0:
        score = min(score, 1)

    score = max(0, min(3, score))
    return (
        AssuranceLevel.HIGH,
        AssuranceLevel.MODERATE,
        AssuranceLevel.GUARDED,
        AssuranceLevel.LOW,
    )[3 - score]


def _resilience(level: AssuranceLevel) -> DecisionResilience:
    return {
        AssuranceLevel.HIGH: DecisionResilience.ROBUST,
        AssuranceLevel.MODERATE: DecisionResilience.ADEQUATE,
        AssuranceLevel.GUARDED: DecisionResilience.FRAGILE,
        AssuranceLevel.LOW: DecisionResilience.BRITTLE,
    }[level]


def _drivers(
    *,
    agreement: AgreementQuality,
    agree_frac: float,
    hard_dissent: list,
    soft_dissent: list,
    single_dep: bool,
    dominant: str | None,
    mos_available: bool,
    evidence_consistency: EvidenceConsistency,
    assumption_risk: AssumptionRiskLevel,
) -> tuple[ConfidenceDriver, ...]:
    drivers: list[ConfidenceDriver] = [
        ConfidenceDriver(
            code="agreement",
            direction=DriverDirection.SUPPORTS
            if agree_frac >= 0.75
            else DriverDirection.WEAKENS
            if agree_frac <= 0.5
            else DriverDirection.SUPPORTS,
            statement=f"Agreement quality is {agreement.value} ({agree_frac:.0%} aligned).",
        )
    ]
    if hard_dissent:
        names = ", ".join(v.source for v in hard_dissent)
        drivers.append(
            ConfidenceDriver(
                code="hard_dissent",
                direction=DriverDirection.WEAKENS,
                statement=f"Hard dissent present from {names}.",
            )
        )
    if soft_dissent:
        names = ", ".join(v.source for v in soft_dissent)
        drivers.append(
            ConfidenceDriver(
                code="soft_dissent",
                direction=DriverDirection.WEAKENS,
                statement=f"Soft dissent (HOLD) from {names}.",
            )
        )
    if single_dep:
        drivers.append(
            ConfidenceDriver(
                code="single_engine",
                direction=DriverDirection.WEAKENS,
                statement=(
                    f"Directional outcome depends heavily on {dominant or 'one member'}."
                ),
            )
        )
    if mos_available:
        drivers.append(
            ConfidenceDriver(
                code="mos_available",
                direction=DriverDirection.SUPPORTS,
                statement="Margin of Safety is available on the recommendation.",
            )
        )
    else:
        drivers.append(
            ConfidenceDriver(
                code="mos_unavailable",
                direction=DriverDirection.WEAKENS,
                statement="Margin of Safety is unavailable on the recommendation.",
            )
        )
    drivers.append(
        ConfidenceDriver(
            code="evidence",
            direction=DriverDirection.SUPPORTS
            if evidence_consistency is EvidenceConsistency.ALIGNED
            else DriverDirection.WEAKENS,
            statement=f"Supporting evidence consistency is {evidence_consistency.value}.",
        )
    )
    if assumption_risk is not AssumptionRiskLevel.LOW:
        drivers.append(
            ConfidenceDriver(
                code="assumption_risk",
                direction=DriverDirection.WEAKENS,
                statement=f"Assumption risk is {assumption_risk.value}.",
            )
        )
    return tuple(drivers)


def _strengths(
    drivers: tuple[ConfidenceDriver, ...],
    agreement: AgreementQuality,
    mos_available: bool,
    agreeing: list,
) -> tuple[str, ...]:
    items: list[str] = []
    if agreement in {
        AgreementQuality.UNANIMOUS,
        AgreementQuality.STRONG_MAJORITY,
    }:
        items.append(f"Strong committee agreement ({agreement.value}).")
    if mos_available:
        items.append("Margin of Safety available to support valuation transparency.")
    if len(agreeing) >= 3:
        items.append("Multiple members support the final action.")
    for d in drivers:
        if d.direction is DriverDirection.SUPPORTS and d.code == "evidence":
            items.append(d.statement)
    if not items:
        items.append("Recommendation reflects the completed committee process.")
    return tuple(items)


def _fragilities(
    drivers: tuple[ConfidenceDriver, ...],
    single_dep: bool,
    hard_dissent: list,
    soft_dissent: list,
    assumption_risk: AssumptionRiskLevel,
) -> tuple[str, ...]:
    items: list[str] = []
    if single_dep:
        items.append("Outcome is concentrated in a single supporting member.")
    if hard_dissent:
        items.append("Hard dissent exists against the final action.")
    if soft_dissent:
        items.append("One or more members abstained with HOLD.")
    if assumption_risk is AssumptionRiskLevel.HIGH:
        items.append("Critical assumptions are fragile.")
    elif assumption_risk is AssumptionRiskLevel.ELEVATED:
        items.append("Assumption risk is elevated.")
    for d in drivers:
        if d.direction is DriverDirection.WEAKENS and d.code == "mos_unavailable":
            items.append(d.statement)
    if not items:
        items.append("No material structural fragilities detected.")
    return tuple(items)


def _review_triggers(
    *,
    recommendation: Recommendation,
    hard_dissent: list,
    soft_dissent: list,
    mos_available: bool,
    agreeing: list,
) -> tuple[ReviewTrigger, ...]:
    triggers: list[ReviewTrigger] = []
    if mos_available:
        triggers.append(
            ReviewTrigger(
                condition="Margin of Safety compresses materially vs intrinsic mid.",
                urgency=ReviewUrgency.ONGOING,
            )
        )
    if any(v.source == "fundamental" for v in agreeing) or any(
        v.source == "fundamental" for v in hard_dissent + soft_dissent
    ):
        triggers.append(
            ReviewTrigger(
                condition="Next earnings / fundamental statement release.",
                urgency=ReviewUrgency.NEXT_EVENT,
            )
        )
    if any(v.source == "economic" for v in agreeing + hard_dissent + soft_dissent):
        triggers.append(
            ReviewTrigger(
                condition="Macro regime shift affecting the economic member stance.",
                urgency=ReviewUrgency.ONGOING,
            )
        )
    if hard_dissent:
        triggers.append(
            ReviewTrigger(
                condition="Dissenting member obtains additional confirming evidence.",
                urgency=ReviewUrgency.IMMEDIATE,
            )
        )
    if recommendation.action is RecommendationAction.HOLD:
        triggers.append(
            ReviewTrigger(
                condition="Committee forms a clear BUY or SELL majority.",
                urgency=ReviewUrgency.NEXT_EVENT,
            )
        )
    if not triggers:
        triggers.append(
            ReviewTrigger(
                condition="Material new evidence arrives for any participating member.",
                urgency=ReviewUrgency.ONGOING,
            )
        )
    return tuple(triggers)


def _guidance(
    *,
    level: AssuranceLevel,
    recommendation: Recommendation,
    agreement: AgreementQuality,
    single_dep: bool,
    mos_available: bool,
    hard_dissent: list,
    agreeing: list,
) -> InvestorGuidance:
    action = recommendation.action
    buy_like = action in {
        RecommendationAction.BUY,
        RecommendationAction.STRONG_BUY,
    }
    sell_like = action in {
        RecommendationAction.SELL,
        RecommendationAction.STRONG_SELL,
    }
    valuation_led = any(v.source == "valuation" for v in agreeing)
    economic_led = any(v.source == "economic" for v in agreeing)
    fundamental_involved = any(
        v.source == "fundamental" for v in agreeing
    ) or any(v.source == "fundamental" for v in hard_dissent)

    # HOLD is never an engagement instruction to buy or sell.
    if action is RecommendationAction.HOLD:
        if agreement is AgreementQuality.UNANIMOUS and level in {
            AssuranceLevel.HIGH,
            AssuranceLevel.MODERATE,
        }:
            rationale = (
                "Committee is aligned on HOLD; stand aside until a "
                "directional majority forms."
            )
        elif agreement is AgreementQuality.CONFLICT or level is AssuranceLevel.LOW:
            rationale = (
                "Committee outcome is unresolved or low-assurance; "
                "do not add exposure on this deliberation alone."
            )
        else:
            rationale = (
                "Recommendation is HOLD; do not add exposure on this "
                "deliberation alone."
            )
        return InvestorGuidance(
            stance=GuidanceStance.STAND_ASIDE, rationale=rationale
        )

    if agreement is AgreementQuality.CONFLICT or level is AssuranceLevel.LOW:
        return InvestorGuidance(
            stance=GuidanceStance.STAND_ASIDE,
            rationale=(
                "Assurance is low or the committee outcome is unresolved; "
                "do not add exposure on this deliberation alone."
            ),
        )

    # Valuation-supported directional calls without usable MoS wait.
    if valuation_led and not mos_available:
        return InvestorGuidance(
            stance=GuidanceStance.WAIT_FOR_CONFIRMATION,
            rationale=(
                "Valuation supports the directional call but Margin of Safety "
                "is unavailable; wait for confirmation before acting."
            ),
        )

    if level is AssuranceLevel.GUARDED or single_dep:
        if valuation_led and mos_available:
            return InvestorGuidance(
                stance=GuidanceStance.WATCH_VALUATION,
                rationale=(
                    "Decision depends on a concentrated valuation thesis; "
                    "watch MoS before committing fully."
                ),
            )
        return InvestorGuidance(
            stance=GuidanceStance.WAIT_FOR_CONFIRMATION,
            rationale=(
                "Assurance is guarded; wait for broader confirmation "
                "before acting on the recommendation."
            ),
        )

    if level is AssuranceLevel.MODERATE:
        if sell_like:
            if fundamental_involved:
                return InvestorGuidance(
                    stance=GuidanceStance.REVIEW_AFTER_EARNINGS,
                    rationale=(
                        "Moderate assurance on a SELL with fundamental "
                        "involvement; reduce only after confirming the next "
                        "fundamental update — do not add long exposure."
                    ),
                )
            return InvestorGuidance(
                stance=GuidanceStance.WAIT_FOR_CONFIRMATION,
                rationale=(
                    "Moderate assurance on a SELL; confirm before accelerating "
                    "risk reduction. Do not add long exposure."
                ),
            )
        if fundamental_involved and buy_like:
            return InvestorGuidance(
                stance=GuidanceStance.ACCUMULATE_GRADUALLY,
                rationale=(
                    "Moderate assurance supports gradual accumulation; "
                    "revisit after fresh fundamental confirmation."
                ),
            )
        if economic_led:
            return InvestorGuidance(
                stance=GuidanceStance.MONITOR_MACRO_CHANGE,
                rationale=(
                    "Macro support is material; monitor regime change closely "
                    "while sizing cautiously."
                ),
            )
        return InvestorGuidance(
            stance=GuidanceStance.ACCUMULATE_GRADUALLY,
            rationale=(
                "Moderate assurance supports staged engagement rather than "
                "an immediate full commitment."
            ),
        )

    # HIGH
    if hard_dissent:
        if sell_like:
            return InvestorGuidance(
                stance=GuidanceStance.WAIT_FOR_CONFIRMATION,
                rationale=(
                    "Assurance is high but hard dissent remains on a SELL; "
                    "confirm before accelerating risk reduction."
                ),
            )
        return InvestorGuidance(
            stance=GuidanceStance.ACCUMULATE_GRADUALLY,
            rationale=(
                "Assurance is high but hard dissent remains; engage gradually."
            ),
        )
    if valuation_led and mos_available and buy_like:
        return InvestorGuidance(
            stance=GuidanceStance.INVEST_IMMEDIATELY,
            rationale=(
                "High assurance with available MoS and broad support; "
                "the deliberation structure supports prompt engagement."
            ),
        )
    if sell_like:
        return InvestorGuidance(
            stance=GuidanceStance.INVEST_IMMEDIATELY,
            rationale=(
                "High assurance on SELL; the deliberation structure supports "
                "prompt risk reduction."
            ),
        )
    return InvestorGuidance(
        stance=GuidanceStance.ACCUMULATE_GRADUALLY,
        rationale=(
            "High assurance overall; staged engagement remains prudent "
            "given residual soft dissent or mixed drivers."
        ),
    )


def _robustness_summary(
    *,
    level: AssuranceLevel,
    agreement: AgreementQuality,
    resilience: DecisionResilience,
    single_dep: bool,
    dominant: str | None,
) -> str:
    dep = (
        f" Single-engine dependence on {dominant}."
        if single_dep and dominant
        else ""
    )
    return (
        f"Assurance is {level.value} with {agreement.value} agreement "
        f"and {resilience.value} resilience.{dep}"
    )
