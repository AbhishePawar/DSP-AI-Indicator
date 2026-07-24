"""Qualitative observation builders from DecisionPack summaries.

Produces explanations of differences — never scores or rankings.
"""

from __future__ import annotations

from industry import ComparisonDimension
from universe import ComparableDecisionSummary

from comparison.models import (
    ComparisonDimensionResult,
    ComparisonLimitation,
    ComparisonObservation,
)

__all__ = [
    "build_decision_context",
    "build_dimension_results",
    "build_limitations",
    "build_pair_observations",
    "build_research_priorities",
    "build_robustness_context",
    "build_shared_observations",
    "build_valuation_context",
]

_ASSURANCE_ORDER = ("low", "guarded", "moderate", "high")
_AGREEMENT_ORDER = (
    "conflict",
    "narrow",
    "majority",
    "strong_majority",
    "unanimous",
)


def build_shared_observations(
    summaries: tuple[ComparableDecisionSummary, ...],
) -> tuple[ComparisonObservation, ...]:
    if len(summaries) < 2:
        return ()
    symbols = tuple(s.instrument.symbol for s in summaries)
    notes: list[ComparisonObservation] = []

    levels = {s.assurance_level.value for s in summaries}
    if len(levels) == 1:
        level = next(iter(levels))
        notes.append(
            ComparisonObservation(
                code="shared_assurance",
                text=(
                    f"All included companies report {level} decision assurance "
                    f"under their Decision Packs."
                ),
                dimension=ComparisonDimension.DECISION_ROBUSTNESS,
                subjects=symbols,
                evidence_refs=("assurance.assurance_level",),
            )
        )

    actions = {s.action.value for s in summaries}
    if len(actions) == 1:
        action = next(iter(actions))
        notes.append(
            ComparisonObservation(
                code="shared_action",
                text=(
                    f"All included companies currently carry a {action} "
                    f"recommendation action."
                ),
                subjects=symbols,
                evidence_refs=("recommendation.action",),
            )
        )

    mos_ok = [s for s in summaries if s.mos_available and s.mos_ratio is not None]
    if len(mos_ok) == len(summaries) and len(mos_ok) >= 2:
        notes.append(
            ComparisonObservation(
                code="shared_mos_available",
                text=(
                    "Margin of safety figures are available for all included "
                    "companies under the current packs."
                ),
                dimension=ComparisonDimension.VALUATION,
                subjects=symbols,
                evidence_refs=("recommendation.margin_of_safety",),
            )
        )

    return tuple(notes)


def build_pair_observations(
    left: ComparableDecisionSummary,
    right: ComparableDecisionSummary,
) -> tuple[ComparisonObservation, ...]:
    a, b = left.instrument.symbol, right.instrument.symbol
    notes: list[ComparisonObservation] = []

    # Valuation / MoS
    if (
        left.mos_available
        and right.mos_available
        and left.mos_ratio is not None
        and right.mos_ratio is not None
    ):
        if left.mos_ratio > right.mos_ratio:
            notes.append(
                ComparisonObservation(
                    code="mos_differential",
                    text=(
                        f"{a} has a larger reported margin of safety than {b} "
                        f"({left.mos_ratio:.1%} vs {right.mos_ratio:.1%})."
                    ),
                    dimension=ComparisonDimension.VALUATION,
                    subjects=(a, b),
                    evidence_refs=("mos_ratio",),
                )
            )
        elif right.mos_ratio > left.mos_ratio:
            notes.append(
                ComparisonObservation(
                    code="mos_differential",
                    text=(
                        f"{b} has a larger reported margin of safety than {a} "
                        f"({right.mos_ratio:.1%} vs {left.mos_ratio:.1%})."
                    ),
                    dimension=ComparisonDimension.VALUATION,
                    subjects=(a, b),
                    evidence_refs=("mos_ratio",),
                )
            )
        else:
            notes.append(
                ComparisonObservation(
                    code="mos_similar",
                    text=(
                        f"{a} and {b} report similar margins of safety "
                        f"({left.mos_ratio:.1%})."
                    ),
                    dimension=ComparisonDimension.VALUATION,
                    subjects=(a, b),
                    evidence_refs=("mos_ratio",),
                )
            )

    # Assurance / robustness
    la, ra = left.assurance_level.value, right.assurance_level.value
    if la != ra:
        if _ASSURANCE_ORDER.index(la) > _ASSURANCE_ORDER.index(ra):
            higher, lower, high_lvl, low_lvl = a, b, la, ra
        else:
            higher, lower, high_lvl, low_lvl = b, a, ra, la
        notes.append(
            ComparisonObservation(
                code="assurance_differential",
                text=(
                    f"{higher} reports a higher assurance level ({high_lvl}) "
                    f"than {lower} ({low_lvl})."
                ),
                dimension=ComparisonDimension.DECISION_ROBUSTNESS,
                subjects=(a, b),
                evidence_refs=("assurance_level",),
            )
        )
    else:
        notes.append(
            ComparisonObservation(
                code="assurance_aligned",
                text=(
                    f"Both {a} and {b} exhibit {la} decision assurance."
                ),
                dimension=ComparisonDimension.DECISION_ROBUSTNESS,
                subjects=(a, b),
                evidence_refs=("assurance_level",),
            )
        )

    # Agreement / consensus
    lq, rq = left.agreement_quality, right.agreement_quality
    if lq != rq:
        try:
            left_stronger = _AGREEMENT_ORDER.index(lq) > _AGREEMENT_ORDER.index(rq)
        except ValueError:
            left_stronger = lq > rq
        stronger = a if left_stronger else b
        notes.append(
            ComparisonObservation(
                code="agreement_differential",
                text=(
                    f"Committee agreement is stronger for {stronger} "
                    f"({lq if left_stronger else rq} vs "
                    f"{rq if left_stronger else lq})."
                ),
                dimension=ComparisonDimension.DECISION_ROBUSTNESS,
                subjects=(a, b),
                evidence_refs=("agreement_quality",),
            )
        )

    # Guidance
    if left.guidance != right.guidance:
        notes.append(
            ComparisonObservation(
                code="guidance_differential",
                text=(
                    f"Investor guidance differs: {a} → {left.guidance.value}; "
                    f"{b} → {right.guidance.value}."
                ),
                subjects=(a, b),
                evidence_refs=("investor_guidance.stance",),
            )
        )

    # Fragilities
    if left.primary_fragility and right.primary_fragility:
        if left.primary_fragility != right.primary_fragility:
            notes.append(
                ComparisonObservation(
                    code="fragility_contrast",
                    text=(
                        f"Primary fragilities differ: {a} cites "
                        f"“{left.primary_fragility}”; {b} cites "
                        f"“{right.primary_fragility}”."
                    ),
                    dimension=ComparisonDimension.RISK,
                    subjects=(a, b),
                    evidence_refs=("key_fragilities",),
                )
            )

    return tuple(notes)


def build_decision_context(
    summaries: tuple[ComparableDecisionSummary, ...],
) -> tuple[ComparisonObservation, ...]:
    notes: list[ComparisonObservation] = []
    for summary in summaries:
        notes.append(
            ComparisonObservation(
                code="decision_snapshot",
                text=(
                    f"{summary.instrument.symbol}: action={summary.action.value}, "
                    f"conviction={summary.conviction:.2f}, "
                    f"guidance={summary.guidance.value}."
                ),
                subjects=(summary.instrument.symbol,),
                evidence_refs=("recommendation", "investor_guidance"),
            )
        )
    return tuple(notes)


def build_valuation_context(
    summaries: tuple[ComparableDecisionSummary, ...],
) -> tuple[ComparisonObservation, ...]:
    notes: list[ComparisonObservation] = []
    for summary in summaries:
        sym = summary.instrument.symbol
        if not summary.mos_available or summary.mos_ratio is None:
            notes.append(
                ComparisonObservation(
                    code="valuation_unavailable",
                    text=(
                        f"{sym} lacks an available margin of safety in the "
                        f"current Decision Pack; valuation context is incomplete."
                    ),
                    dimension=ComparisonDimension.VALUATION,
                    subjects=(sym,),
                    evidence_refs=("margin_of_safety",),
                )
            )
        else:
            mid = summary.intrinsic_mid
            mid_note = (
                f" Intrinsic mid={mid} {summary.intrinsic_currency or ''}.".rstrip()
                if mid is not None
                else ""
            )
            notes.append(
                ComparisonObservation(
                    code="valuation_snapshot",
                    text=(
                        f"{sym} reports MoS={summary.mos_ratio:.1%}."
                        f"{mid_note}"
                    ),
                    dimension=ComparisonDimension.VALUATION,
                    subjects=(sym,),
                    evidence_refs=("margin_of_safety", "valuation_summary"),
                )
            )
    return tuple(notes)


def build_robustness_context(
    summaries: tuple[ComparableDecisionSummary, ...],
) -> tuple[ComparisonObservation, ...]:
    notes: list[ComparisonObservation] = []
    for summary in summaries:
        sym = summary.instrument.symbol
        dissent = (
            f" Dissenting sources: {', '.join(summary.dissenting_sources)}."
            if summary.dissenting_sources
            else " No dissenting sources recorded."
        )
        notes.append(
            ComparisonObservation(
                code="robustness_snapshot",
                text=(
                    f"{sym}: assurance={summary.assurance_level.value}, "
                    f"agreement={summary.agreement_quality}.{dissent}"
                ),
                dimension=ComparisonDimension.DECISION_ROBUSTNESS,
                subjects=(sym,),
                evidence_refs=("assurance", "agreement_quality"),
            )
        )
    return tuple(notes)


def build_dimension_results(
    dimensions: tuple[ComparisonDimension, ...],
    shared: tuple[ComparisonObservation, ...],
    pairs: tuple[ComparisonObservation, ...],
) -> tuple[ComparisonDimensionResult, ...]:
    results: list[ComparisonDimensionResult] = []
    all_obs = (*shared, *pairs)
    for dimension in dimensions:
        matching = tuple(o for o in all_obs if o.dimension is dimension)
        if matching:
            results.append(
                ComparisonDimensionResult(
                    dimension=dimension, observations=matching
                )
            )
        else:
            results.append(
                ComparisonDimensionResult(
                    dimension=dimension,
                    observations=(
                        ComparisonObservation(
                            code="dimension_no_pack_signal",
                            text=(
                                f"No Decision Pack signal mapped to the "
                                f"{dimension.value} dimension in this run; "
                                f"treat as a research gap, not an absence of risk."
                            ),
                            dimension=dimension,
                        ),
                    ),
                )
            )
    return tuple(results)


def build_limitations(
    summaries: tuple[ComparableDecisionSummary, ...],
    *,
    excluded: tuple[str, ...],
    exclusion_reasons: tuple[str, ...],
    methodology_gaps: tuple[str, ...] = (),
    degraded: bool = False,
) -> tuple[ComparisonLimitation, ...]:
    limits: list[ComparisonLimitation] = []
    limits.append(
        ComparisonLimitation(
            code="qualitative_only",
            message=(
                "This report is qualitative only. It does not score, rank, "
                "or declare a preferred investment."
            ),
        )
    )
    if degraded:
        limits.append(
            ComparisonLimitation(
                code="degraded_scope",
                message=(
                    "Comparison scope was reduced because some instruments "
                    "failed peer eligibility or methodology alignment."
                ),
                subjects=excluded,
            )
        )
    for reason in exclusion_reasons:
        limits.append(
            ComparisonLimitation(
                code="exclusion",
                message=reason,
                subjects=excluded,
            )
        )
    for summary in summaries:
        if not summary.mos_available or summary.mos_ratio is None:
            limits.append(
                ComparisonLimitation(
                    code="missing_valuation",
                    message=(
                        f"{summary.instrument.symbol} is missing an available "
                        f"margin of safety."
                    ),
                    subjects=(summary.instrument.symbol,),
                )
            )
        if summary.primary_fragility:
            limits.append(
                ComparisonLimitation(
                    code="recorded_fragility",
                    message=(
                        f"{summary.instrument.symbol} fragility: "
                        f"{summary.primary_fragility}"
                    ),
                    subjects=(summary.instrument.symbol,),
                )
            )
    for gap in methodology_gaps:
        limits.append(
            ComparisonLimitation(code="methodology_gap", message=gap)
        )
    limits.append(
        ComparisonLimitation(
            code="no_certainty",
            message=(
                "Incomplete evidence or methodology gaps may remain. "
                "Comparison must not be read as certainty."
            ),
        )
    )
    return tuple(limits)


def build_research_priorities(
    limitations: tuple[ComparisonLimitation, ...],
    dimensions: tuple[ComparisonDimension, ...],
    dimension_results: tuple[ComparisonDimensionResult, ...],
) -> tuple[str, ...]:
    priorities: list[str] = []
    for lim in limitations:
        if lim.code in {"missing_valuation", "methodology_gap", "exclusion"}:
            priorities.append(lim.message)
    for result in dimension_results:
        if any(o.code == "dimension_no_pack_signal" for o in result.observations):
            priorities.append(
                f"Gather industry-appropriate evidence for dimension "
                f"{result.dimension.value}."
            )
    # Stable unique
    return tuple(dict.fromkeys(priorities))
