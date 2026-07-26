"""Deterministic committee reviewers (no LLM / ML)."""

from __future__ import annotations

from investment_committee.models import (
    CommitteeEvidence,
    CommitteeScore,
    InvestmentCommitteeConfidence,
    ReviewerOpinion,
)
from investment_committee.scoring import (
    ReviewerRole,
    clip_score,
    decision_from_score,
)
from investment_committee.signals import CommitteeSignals

__all__ = ["evaluate_all_reviewers"]

_STRONG = 70.0
_WEAK = 45.0


def _mean(values: list[float | None]) -> float | None:
    present = [float(v) for v in values if v is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _score(value: float | None) -> CommitteeScore:
    if value is None:
        return CommitteeScore(value=None, status="insufficient_data")
    return CommitteeScore(value=round(clip_score(value), 4), status="assessed")


def _conf(value: float, *, basis: str) -> InvestmentCommitteeConfidence:
    return InvestmentCommitteeConfidence(
        value=round(max(0.0, min(1.0, value)), 4), basis=basis
    )


def _evidence(
    role: ReviewerRole,
    *,
    reference: str,
    summary: str,
    reasoning: str,
    confidence: float,
    metrics: list[str],
    limitations: list[str],
) -> CommitteeEvidence:
    return CommitteeEvidence(
        source=role.value,
        reference=reference,
        summary=summary,
        reasoning=reasoning,
        confidence=confidence,
        supporting_metrics=tuple(metrics),
        limitations=tuple(limitations),
        contributing_reviewers=(role.value,),
    )


def _buffett(signals: CommitteeSignals) -> ReviewerOpinion:
    mos_score = None
    if signals.mos_ratio is not None:
        mos_score = clip_score(50.0 + signals.mos_ratio * 100.0)
    value = _mean(
        [
            signals.economic_moat,
            signals.management_quality,
            signals.business_quality,
            mos_score,
        ]
    )
    factors: list[str] = []
    concerns: list[str] = []
    if signals.economic_moat is not None and signals.economic_moat >= _STRONG:
        factors.append("Durable competitive advantage (moat)")
    if signals.management_quality is not None and signals.management_quality < _WEAK:
        concerns.append("Capital allocation / management quality is weak")
    if signals.mos_ratio is not None and signals.mos_ratio < 0:
        concerns.append("Insufficient margin of safety")
    if signals.mos_ratio is not None and signals.mos_ratio >= 0.25:
        factors.append("Attractive margin of safety")
    conf = _mean(
        [signals.bq_confidence, signals.ir_confidence, signals.valuation_confidence]
    ) or 0.4
    role = ReviewerRole.BUFFETT_ANALYST
    return ReviewerOpinion(
        role=role,
        opinion=decision_from_score(value),
        score=_score(value),
        confidence=_conf(conf, basis="buffett_blend"),
        evidence=[
            _evidence(
                role,
                reference="moat_mgmt_mos",
                summary="Buffett lens: moat, management, MoS, durability",
                reasoning=(
                    "Scores durable franchise quality and insists on a MoS buffer; "
                    "does not reward growth without capital discipline."
                ),
                confidence=conf,
                metrics=[
                    f"moat={signals.economic_moat}",
                    f"management={signals.management_quality}",
                    f"business_quality={signals.business_quality}",
                    f"mos={signals.mos_ratio}",
                ],
                limitations=["Qualitative franchise nuances not modeled"],
            )
        ],
        supporting_factors=tuple(factors),
        concerns=tuple(concerns),
        limitations=("Deterministic Buffett proxy — not a forecast.",),
        reasoning="Focuses on moat, owner-oriented management, and MoS durability.",
    )


def _value(signals: CommitteeSignals) -> ReviewerOpinion:
    mos_score = None
    if signals.mos_ratio is not None:
        mos_score = clip_score(50.0 + signals.mos_ratio * 120.0)
    value = _mean([mos_score, signals.business_quality, signals.financial_strength])
    factors: list[str] = []
    concerns: list[str] = []
    if signals.mos_ratio is not None and signals.mos_ratio >= 0.20:
        factors.append("Material valuation discount / MoS")
    if signals.premium_discount is not None and signals.premium_discount >= 0.25:
        concerns.append("Material premium to intrinsic value")
        if value is not None:
            value = clip_score(value - 12.0)
    if (
        signals.earnings_quality is not None
        and signals.earnings_quality < _WEAK
        and signals.mos_ratio is not None
        and signals.mos_ratio > 0.15
    ):
        concerns.append("Cheap valuation with deteriorating/weak earnings quality")
        if value is not None:
            value = clip_score(value - 8.0)
    conf = _mean([signals.valuation_confidence, signals.ir_confidence]) or 0.4
    role = ReviewerRole.VALUE_INVESTOR
    return ReviewerOpinion(
        role=role,
        opinion=decision_from_score(value),
        score=_score(value),
        confidence=_conf(conf, basis="value_blend"),
        evidence=[
            _evidence(
                role,
                reference="intrinsic_value_mos",
                summary="Value lens: IV discount and downside protection",
                reasoning=(
                    "Prioritises intrinsic-value discount and balance-sheet support; "
                    "penalises value traps with weak earnings quality."
                ),
                confidence=conf,
                metrics=[
                    f"mos={signals.mos_ratio}",
                    f"premium={signals.premium_discount}",
                    f"strength={signals.financial_strength}",
                    f"earnings={signals.earnings_quality}",
                ],
                limitations=["IV model error can misstate MoS"],
            )
        ],
        supporting_factors=tuple(factors),
        concerns=tuple(concerns),
        limitations=("Deterministic value proxy — research only.",),
        reasoning="Focuses on intrinsic value, discount, and downside protection.",
    )


def _quality(signals: CommitteeSignals) -> ReviewerOpinion:
    value = _mean(
        [
            signals.financial_strength,
            signals.earnings_quality,
            signals.business_quality,
        ]
    )
    factors: list[str] = []
    concerns: list[str] = []
    if signals.financial_strength is not None and signals.financial_strength >= _STRONG:
        factors.append("Strong financial strength")
    if signals.earnings_quality is not None and signals.earnings_quality >= _STRONG:
        factors.append("High earnings quality")
    if signals.business_quality is not None and signals.business_quality < _WEAK:
        concerns.append("Weak overall business quality")
    if signals.bq_confidence < 0.4:
        concerns.append("Low business-quality confidence")
        if value is not None:
            value = clip_score(value - 5.0)
    conf = _mean([signals.bq_confidence, signals.ir_confidence]) or 0.4
    role = ReviewerRole.QUALITY_INVESTOR
    return ReviewerOpinion(
        role=role,
        opinion=decision_from_score(value),
        score=_score(value),
        confidence=_conf(conf, basis="quality_blend"),
        evidence=[
            _evidence(
                role,
                reference="fs_eq_bq",
                summary="Quality lens: FS, earnings quality, business quality",
                reasoning=(
                    "Emphasises cash-backed earnings and balance-sheet resilience "
                    "as prerequisites for compounding."
                ),
                confidence=conf,
                metrics=[
                    f"strength={signals.financial_strength}",
                    f"earnings={signals.earnings_quality}",
                    f"business_quality={signals.business_quality}",
                ],
                limitations=["Does not model industry cyclicality deeply"],
            )
        ],
        supporting_factors=tuple(factors),
        concerns=tuple(concerns),
        limitations=("Deterministic quality proxy — research only.",),
        reasoning="Focuses on financial strength, earnings quality, and BQ.",
    )


def _growth(signals: CommitteeSignals) -> ReviewerOpinion:
    value = _mean(
        [signals.growth_quality, signals.business_quality, signals.economic_moat]
    )
    factors: list[str] = []
    concerns: list[str] = []
    if signals.growth_quality is not None and signals.growth_quality >= _STRONG:
        factors.append("Strong growth quality / reinvestment profile")
    if (
        signals.growth_quality is not None
        and signals.growth_quality >= _STRONG
        and signals.financial_strength is not None
        and signals.financial_strength < _WEAK
    ):
        concerns.append("Excellent growth with weak balance sheet")
        if value is not None:
            value = clip_score(value - 10.0)
    conf = _mean([signals.bq_confidence, signals.ir_confidence]) or 0.4
    role = ReviewerRole.GROWTH_INVESTOR
    return ReviewerOpinion(
        role=role,
        opinion=decision_from_score(value),
        score=_score(value),
        confidence=_conf(conf, basis="growth_blend"),
        evidence=[
            _evidence(
                role,
                reference="growth_reinvestment",
                summary="Growth lens: growth quality, reinvestment, scalability",
                reasoning=(
                    "Favours capital-efficient growth but discounts leverage-funded "
                    "expansion when financial strength is weak."
                ),
                confidence=conf,
                metrics=[
                    f"growth={signals.growth_quality}",
                    f"business_quality={signals.business_quality}",
                    f"strength={signals.financial_strength}",
                ],
                limitations=["Forward growth not forecasted"],
            )
        ],
        supporting_factors=tuple(factors),
        concerns=tuple(concerns),
        limitations=("Deterministic growth proxy — research only.",),
        reasoning="Focuses on growth quality, reinvestment, and scalability.",
    )


def _risk(signals: CommitteeSignals) -> ReviewerOpinion:
    # Higher score = safer (more constructive). Start neutral-high and penalise.
    value = 72.0
    concerns: list[str] = []
    factors: list[str] = []
    if signals.financial_strength is not None and signals.financial_strength < _WEAK:
        value -= 15.0
        concerns.append("Balance-sheet / financial-strength risk")
    elif signals.financial_strength is not None and signals.financial_strength >= _STRONG:
        factors.append("Balance sheet supports resilience")
    if signals.conflict_count > 0:
        value -= min(12.0, 3.0 * signals.conflict_count)
        concerns.append(f"{signals.conflict_count} cross-domain conflict(s)")
    if signals.ir_triggered_rules:
        value -= min(10.0, 2.0 * len(signals.ir_triggered_rules))
        concerns.append("Investment recommendation conflict rules triggered")
    if signals.mos_ratio is not None and signals.mos_ratio < -0.15:
        value -= 12.0
        concerns.append("Negative margin of safety / overvaluation risk")
    if signals.ir_confidence < 0.4 or signals.bq_confidence < 0.4:
        value -= 8.0
        concerns.append("High uncertainty / low confidence inputs")
    if (
        signals.economic_moat is not None
        and signals.economic_moat >= _STRONG
        and signals.management_quality is not None
        and signals.management_quality < _WEAK
    ):
        value -= 8.0
        concerns.append("Strong moat with poor management / capital allocation")
    if (
        signals.business_quality is not None
        and signals.business_quality >= _STRONG
        and signals.mos_ratio is not None
        and signals.mos_ratio < 0
    ):
        concerns.append("Great business / expensive valuation")
    value = clip_score(value)
    conf = _mean(
        [signals.ir_confidence, signals.bq_confidence, signals.valuation_confidence]
    ) or 0.35
    # Risk officer confidence is intentionally tempered
    conf = min(conf, 0.75)
    role = ReviewerRole.RISK_OFFICER
    return ReviewerOpinion(
        role=role,
        opinion=decision_from_score(value),
        score=_score(value),
        confidence=_conf(conf, basis="risk_penalty_model"),
        evidence=[
            _evidence(
                role,
                reference="risk_conflicts_uncertainty",
                summary="Risk lens: BS, conflicts, uncertainty, confidence penalties",
                reasoning=(
                    "Applies deterministic penalties for weak balance sheets, "
                    "cross-domain conflicts, overvaluation, and low confidence."
                ),
                confidence=conf,
                metrics=[
                    f"strength={signals.financial_strength}",
                    f"conflicts={signals.conflict_count}",
                    f"ir_rules={len(signals.ir_triggered_rules)}",
                    f"mos={signals.mos_ratio}",
                    f"ir_confidence={signals.ir_confidence}",
                ],
                limitations=["Not a full enterprise risk model"],
            )
        ],
        supporting_factors=tuple(factors),
        concerns=tuple(concerns),
        limitations=("Deterministic risk proxy — research only.",),
        reasoning="Focuses on downside, conflicts, and confidence penalties.",
    )


def evaluate_all_reviewers(signals: CommitteeSignals) -> tuple[ReviewerOpinion, ...]:
    return (
        _buffett(signals),
        _value(signals),
        _quality(signals),
        _growth(signals),
        _risk(signals),
    )
