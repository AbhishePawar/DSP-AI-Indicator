"""Recommendation Engine — cite-backed synthesis only (G1.2).

Consumes assembled Recommendation context + caller-declared signal postures.
Produces options, scores, rationales, conflicts, and an updated report.
Never re-runs upstream engines, optimizes portfolios, or uses LLM/ML.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from recommendation.assembler import AssemblyResult
from recommendation.enums import (
    ConfidenceLevel,
    ConflictSeverity,
    EngineStatus,
    RecommendationType,
    SignalPosture,
)
from recommendation.exceptions import RecommendationError
from recommendation.models import (
    RecommendationConflict,
    RecommendationOption,
    RecommendationProfile,
    RecommendationRationale,
    RecommendationReport,
    RecommendationScore,
    RecommendationSummary,
)

__all__ = [
    "EngineContext",
    "EngineResult",
    "RecommendationEngine",
]

METHOD_BASELINE = "dsp.recommendation.method.baseline_rules.v1"

_CONFIDENCE_VALUE: dict[ConfidenceLevel, Decimal] = {
    ConfidenceLevel.LOW: Decimal("0.35"),
    ConfidenceLevel.MEDIUM: Decimal("0.55"),
    ConfidenceLevel.HIGH: Decimal("0.75"),
    ConfidenceLevel.VERY_HIGH: Decimal("0.90"),
}


@dataclass(frozen=True, slots=True)
class EngineContext:
    """Inputs for deterministic recommendation synthesis.

    Signal postures are caller-declared summaries bound to cited upstream
    reports — the engine never invents primary analysis.
    """

    assembly: AssemblyResult
    profile: RecommendationProfile | None = None
    qualitative_posture: SignalPosture = SignalPosture.UNKNOWN
    quantitative_posture: SignalPosture = SignalPosture.UNKNOWN
    valuation_posture: SignalPosture = SignalPosture.UNKNOWN
    portfolio_fit: SignalPosture = SignalPosture.UNKNOWN
    calculation_timestamp: str | None = None

    def __post_init__(self) -> None:
        if self.assembly is None:
            msg = "AssemblyResult is required"
            raise RecommendationError(msg)
        timestamp = (
            None
            if self.calculation_timestamp is None
            else self.calculation_timestamp.strip() or None
        )
        object.__setattr__(self, "calculation_timestamp", timestamp)


@dataclass(frozen=True, slots=True)
class EngineResult:
    """Immutable engine output."""

    recommendation_id: str
    status: EngineStatus
    profile: RecommendationProfile
    report: RecommendationReport
    options: tuple[RecommendationOption, ...]
    scores: tuple[RecommendationScore, ...]
    rationales: tuple[RecommendationRationale, ...]
    conflicts: tuple[RecommendationConflict, ...]
    summary: RecommendationSummary
    preferred_option_id: str | None
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "options", tuple(self.options))
        object.__setattr__(self, "scores", tuple(self.scores))
        object.__setattr__(self, "rationales", tuple(self.rationales))
        object.__setattr__(self, "conflicts", tuple(self.conflicts))
        object.__setattr__(self, "warnings", tuple(self.warnings))


class RecommendationEngine:
    """Canonical cite-backed recommendation synthesis layer (baseline rules)."""

    def validate_inputs(self, context: EngineContext) -> None:
        """Reject invalid synthesis inputs."""
        if context is None or context.assembly is None:
            msg = "EngineContext.assembly is required"
            raise RecommendationError(msg)
        profile = context.profile or context.assembly.profile
        if profile is None or profile.identity is None:
            msg = "missing RecommendationProfile"
            raise RecommendationError(msg)
        if not profile.decision_refs:
            msg = "missing Decision reference"
            raise RecommendationError(msg)
        if not profile.comparison_refs:
            msg = "missing Comparison reference"
            raise RecommendationError(msg)
        if profile.portfolio_ref is None:
            msg = "missing Portfolio reference"
            raise RecommendationError(msg)
        if not profile.risk_refs:
            msg = "missing Risk reference"
            raise RecommendationError(msg)
        if not profile.research_refs:
            msg = "missing Research reference"
            raise RecommendationError(msg)
        if not profile.quantitative_risk_refs:
            msg = "missing Quantitative Risk reference"
            raise RecommendationError(msg)
        if (
            context.profile is not None
            and context.profile.recommendation_id
            != context.assembly.profile.recommendation_id
        ):
            msg = (
                "broken references: profile recommendation_id does not match assembly"
            )
            raise RecommendationError(msg)

    def synthesize(
        self, context: EngineContext | AssemblyResult
    ) -> EngineResult:
        """Run baseline rule synthesis and emit an updated recommendation report."""
        ctx = (
            EngineContext(assembly=context)
            if isinstance(context, AssemblyResult)
            else context
        )
        self.validate_inputs(ctx)
        profile = ctx.profile or ctx.assembly.profile
        base_report = ctx.assembly.report
        rid = profile.recommendation_id
        timestamp = ctx.calculation_timestamp or base_report.as_of
        citations = self._citation_keys(profile)
        provenance = tuple(sorted(citations))
        warnings: list[str] = []

        unknown_count = sum(
            1
            for p in (
                ctx.qualitative_posture,
                ctx.quantitative_posture,
                ctx.valuation_posture,
                ctx.portfolio_fit,
            )
            if p is SignalPosture.UNKNOWN
        )
        if unknown_count:
            warnings.append(
                f"{unknown_count} signal posture(s) UNKNOWN — "
                "baseline treats unknown as incomplete directional coverage."
            )

        conflicts = self._detect_conflicts(
            recommendation_id=rid,
            qualitative=ctx.qualitative_posture,
            quantitative=ctx.quantitative_posture,
            valuation=ctx.valuation_posture,
            portfolio_fit=ctx.portfolio_fit,
            citations=citations,
            unknown_count=unknown_count,
        )
        preferred_type, alt_type = self._select_option_types(
            qualitative=ctx.qualitative_posture,
            quantitative=ctx.quantitative_posture,
            valuation=ctx.valuation_posture,
            portfolio_fit=ctx.portfolio_fit,
            conflicts=conflicts,
            unknown_count=unknown_count,
        )
        confidence = self._confidence(
            qualitative=ctx.qualitative_posture,
            quantitative=ctx.quantitative_posture,
            valuation=ctx.valuation_posture,
            portfolio_fit=ctx.portfolio_fit,
            conflicts=conflicts,
            unknown_count=unknown_count,
        )

        score = RecommendationScore(
            score_id=f"dsp.recommendation.score.confidence.{rid}",
            score_type="confidence",
            value=_CONFIDENCE_VALUE[confidence],
            unit="confidence_fraction",
            method_id=METHOD_BASELINE,
            provenance=provenance,
            calculation_timestamp=timestamp,
            confidence_level=confidence,
            notes=(
                "Confidence reflects evidence agreement, conflict severity, "
                "coverage completeness, and consistency — not market prediction.",
            ),
        )

        preferred_rationale = RecommendationRationale(
            rationale_id=f"dsp.recommendation.rationale.preferred.{rid}",
            title=f"Baseline rationale for {preferred_type.value}",
            body=self._rationale_body(
                option_type=preferred_type,
                qualitative=ctx.qualitative_posture,
                quantitative=ctx.quantitative_posture,
                valuation=ctx.valuation_posture,
                portfolio_fit=ctx.portfolio_fit,
                conflicts=conflicts,
            ),
            supporting_report_refs=tuple(sorted(citations)),
        )
        alt_rationale = RecommendationRationale(
            rationale_id=f"dsp.recommendation.rationale.alternate.{rid}",
            title=f"Alternate posture {alt_type.value}",
            body=(
                f"Alternate transparent option {alt_type.value} retained for "
                "trade-off visibility. Citations unchanged; not a primary analysis."
            ),
            supporting_report_refs=tuple(sorted(citations)),
        )

        preferred_option = RecommendationOption(
            option_id=f"dsp.recommendation.option.preferred.{rid}",
            option_type=preferred_type,
            title=f"Preferred: {preferred_type.value}",
            description=(
                f"Deterministic baseline preference under method {METHOD_BASELINE}."
            ),
            supporting_rationale_refs=(preferred_rationale.rationale_id,),
            supporting_report_refs=tuple(sorted(citations)),
            confidence_reference=score.score_id,
            priority=0,
        )
        alt_option = RecommendationOption(
            option_id=f"dsp.recommendation.option.alternate.{rid}",
            option_type=alt_type,
            title=f"Alternate: {alt_type.value}",
            description="Secondary transparent option for conflict / coverage cases.",
            supporting_rationale_refs=(alt_rationale.rationale_id,),
            supporting_report_refs=tuple(sorted(citations)),
            confidence_reference=score.score_id,
            priority=1,
        )

        options = (preferred_option, alt_option)
        scores = (score,)
        rationales = (preferred_rationale, alt_rationale)

        self._validate_outputs(
            options=options,
            scores=scores,
            rationales=rationales,
            conflicts=conflicts,
            citations=citations,
        )

        summary = RecommendationSummary(
            option_count=len(options),
            conflict_count=len(conflicts),
            rationale_count=len(rationales),
            score_count=len(scores),
            limitation_notes=(
                "Baseline rule synthesis only — no primary analysis, "
                "optimization, or market forecasting.",
                f"Method: {METHOD_BASELINE}",
                *tuple(warnings),
            ),
        )

        updated_profile = RecommendationProfile(
            identity=profile.identity,
            decision_refs=profile.decision_refs,
            comparison_refs=profile.comparison_refs,
            portfolio_ref=profile.portfolio_ref,
            risk_refs=profile.risk_refs,
            research_refs=profile.research_refs,
            quantitative_risk_refs=profile.quantitative_risk_refs,
            options=options,
            scores=scores,
            rationales=rationales,
            conflicts=conflicts,
            summary=summary,
            preferred_option_id=preferred_option.option_id,
            notes=profile.notes,
        )

        report = RecommendationReport(
            recommendation_id=rid,
            summary=summary,
            as_of=base_report.as_of,
            options=options,
            scores=scores,
            rationales=rationales,
            conflicts=conflicts,
            decision_refs=profile.decision_refs,
            comparison_refs=profile.comparison_refs,
            portfolio_ref=profile.portfolio_ref,
            risk_refs=profile.risk_refs,
            research_refs=profile.research_refs,
            quantitative_risk_refs=profile.quantitative_risk_refs,
            preferred_option_id=preferred_option.option_id,
            limitations=(
                *base_report.limitations,
                *summary.limitation_notes,
            ),
        )

        status = EngineStatus.PARTIAL if warnings or conflicts else EngineStatus.COMPLETE
        return EngineResult(
            recommendation_id=rid,
            status=status,
            profile=updated_profile,
            report=report,
            options=options,
            scores=scores,
            rationales=rationales,
            conflicts=conflicts,
            summary=summary,
            preferred_option_id=preferred_option.option_id,
            warnings=tuple(warnings),
        )

    def synthesize_many(
        self, contexts: tuple[EngineContext | AssemblyResult, ...]
    ) -> tuple[EngineResult, ...]:
        """Synthesize many contexts; reject duplicate recommendation identities."""
        seen: set[str] = set()
        results: list[EngineResult] = []
        for item in contexts:
            result = self.synthesize(item)
            if result.recommendation_id in seen:
                msg = (
                    "duplicate identities: recommendation_id "
                    f"{result.recommendation_id!r}"
                )
                raise RecommendationError(msg)
            seen.add(result.recommendation_id)
            results.append(result)
        return tuple(results)

    def _citation_keys(self, profile: RecommendationProfile) -> frozenset[str]:
        keys: set[str] = set()
        for ref in profile.decision_refs:
            keys.add(ref.citation)
        for ref in profile.comparison_refs:
            keys.add(ref.citation)
        if profile.portfolio_ref is not None:
            keys.add(profile.portfolio_ref.citation)
        for ref in profile.risk_refs:
            keys.add(ref.citation)
        for ref in profile.research_refs:
            keys.add(ref.citation)
        for ref in profile.quantitative_risk_refs:
            keys.add(ref.citation)
        return frozenset(keys)

    def _detect_conflicts(
        self,
        *,
        recommendation_id: str,
        qualitative: SignalPosture,
        quantitative: SignalPosture,
        valuation: SignalPosture,
        portfolio_fit: SignalPosture,
        citations: frozenset[str],
        unknown_count: int,
    ) -> tuple[RecommendationConflict, ...]:
        conflicts: list[RecommendationConflict] = []
        report_refs = tuple(sorted(citations))

        if (
            qualitative is SignalPosture.SUPPORTIVE
            and quantitative in {SignalPosture.ADVERSE, SignalPosture.CAUTIONARY}
        ):
            conflicts.append(
                RecommendationConflict(
                    conflict_id=f"dsp.recommendation.conflict.qual_vs_quant.{recommendation_id}",
                    title="Qualitative support vs quantitative risk",
                    description=(
                        "Positive / supportive qualitative posture conflicts with "
                        "cautionary or adverse quantitative risk citation posture."
                    ),
                    severity=ConflictSeverity.HIGH,
                    option_refs=(
                        f"dsp.recommendation.option.preferred.{recommendation_id}",
                        f"dsp.recommendation.option.alternate.{recommendation_id}",
                    ),
                    report_refs=report_refs,
                )
            )

        if (
            valuation is SignalPosture.SUPPORTIVE
            and portfolio_fit in {SignalPosture.ADVERSE, SignalPosture.CAUTIONARY}
        ):
            conflicts.append(
                RecommendationConflict(
                    conflict_id=f"dsp.recommendation.conflict.valuation_vs_fit.{recommendation_id}",
                    title="Strong valuation vs weak portfolio fit",
                    description=(
                        "Supportive valuation / decision posture conflicts with "
                        "cautionary or adverse portfolio-fit posture."
                    ),
                    severity=ConflictSeverity.MEDIUM,
                    option_refs=(
                        f"dsp.recommendation.option.preferred.{recommendation_id}",
                        f"dsp.recommendation.option.alternate.{recommendation_id}",
                    ),
                    report_refs=report_refs,
                )
            )

        if unknown_count >= 2:
            conflicts.append(
                RecommendationConflict(
                    conflict_id=f"dsp.recommendation.conflict.insufficient.{recommendation_id}",
                    title="Insufficient evidence",
                    description=(
                        "Multiple signal postures remain UNKNOWN; directional "
                        "recommendation evidence is incomplete."
                    ),
                    severity=ConflictSeverity.HIGH,
                    option_refs=(
                        f"dsp.recommendation.option.preferred.{recommendation_id}",
                        f"dsp.recommendation.option.alternate.{recommendation_id}",
                    ),
                    report_refs=report_refs,
                )
            )

        return tuple(conflicts)

    def _select_option_types(
        self,
        *,
        qualitative: SignalPosture,
        quantitative: SignalPosture,
        valuation: SignalPosture,
        portfolio_fit: SignalPosture,
        conflicts: tuple[RecommendationConflict, ...],
        unknown_count: int,
    ) -> tuple[RecommendationType, RecommendationType]:
        if unknown_count >= 2 or any(
            c.severity is ConflictSeverity.HIGH
            and "insufficient" in c.conflict_id
            for c in conflicts
        ):
            return (
                RecommendationType.INSUFFICIENT_EVIDENCE,
                RecommendationType.WATCH,
            )

        supportive = sum(
            1
            for p in (qualitative, quantitative, valuation, portfolio_fit)
            if p is SignalPosture.SUPPORTIVE
        )
        adverse = sum(
            1
            for p in (qualitative, quantitative, valuation, portfolio_fit)
            if p in {SignalPosture.ADVERSE, SignalPosture.CAUTIONARY}
        )

        has_qual_quant = any("qual_vs_quant" in c.conflict_id for c in conflicts)
        has_val_fit = any("valuation_vs_fit" in c.conflict_id for c in conflicts)

        if has_qual_quant:
            return RecommendationType.HOLD, RecommendationType.REDUCE
        if has_val_fit:
            return RecommendationType.WATCH, RecommendationType.HOLD
        if supportive >= 3 and adverse == 0:
            return RecommendationType.BUY, RecommendationType.HOLD
        if adverse >= 3 and supportive == 0:
            return RecommendationType.SELL, RecommendationType.REDUCE
        if adverse >= 2:
            return RecommendationType.REDUCE, RecommendationType.HOLD
        if supportive >= 2:
            return RecommendationType.HOLD, RecommendationType.BUY
        return RecommendationType.HOLD, RecommendationType.WATCH

    def _confidence(
        self,
        *,
        qualitative: SignalPosture,
        quantitative: SignalPosture,
        valuation: SignalPosture,
        portfolio_fit: SignalPosture,
        conflicts: tuple[RecommendationConflict, ...],
        unknown_count: int,
    ) -> ConfidenceLevel:
        postures = (qualitative, quantitative, valuation, portfolio_fit)
        known = [p for p in postures if p is not SignalPosture.UNKNOWN]
        if unknown_count >= 2:
            return ConfidenceLevel.LOW
        if not known:
            return ConfidenceLevel.LOW

        agreement = len({p for p in known}) == 1
        high_conflict = any(c.severity is ConflictSeverity.HIGH for c in conflicts)
        medium_conflict = any(c.severity is ConflictSeverity.MEDIUM for c in conflicts)
        coverage_complete = unknown_count == 0

        if high_conflict:
            return ConfidenceLevel.LOW
        if medium_conflict or unknown_count == 1:
            return ConfidenceLevel.MEDIUM
        if agreement and coverage_complete:
            return ConfidenceLevel.VERY_HIGH
        if coverage_complete:
            return ConfidenceLevel.HIGH
        return ConfidenceLevel.MEDIUM

    def _rationale_body(
        self,
        *,
        option_type: RecommendationType,
        qualitative: SignalPosture,
        quantitative: SignalPosture,
        valuation: SignalPosture,
        portfolio_fit: SignalPosture,
        conflicts: tuple[RecommendationConflict, ...],
    ) -> str:
        conflict_titles = ", ".join(c.title for c in conflicts) or "none"
        return (
            f"Preferred posture {option_type.value} selected by baseline rules. "
            f"Qualitative={qualitative.value}; quantitative={quantitative.value}; "
            f"valuation={valuation.value}; portfolio_fit={portfolio_fit.value}. "
            f"Declared conflicts: {conflict_titles}. "
            "All claims cite assembled upstream report references only."
        )

    def _validate_outputs(
        self,
        *,
        options: tuple[RecommendationOption, ...],
        scores: tuple[RecommendationScore, ...],
        rationales: tuple[RecommendationRationale, ...],
        conflicts: tuple[RecommendationConflict, ...],
        citations: frozenset[str],
    ) -> None:
        if not options:
            msg = "missing rationale: engine produced no options"
            raise RecommendationError(msg)
        if not rationales:
            msg = "missing rationale: engine produced no rationales"
            raise RecommendationError(msg)
        if not scores:
            msg = "invalid confidence: engine produced no scores"
            raise RecommendationError(msg)

        option_ids: set[str] = set()
        for option in options:
            if option.option_id in option_ids:
                msg = f"duplicate options: id {option.option_id!r}"
                raise RecommendationError(msg)
            option_ids.add(option.option_id)
            if not option.supporting_report_refs:
                msg = (
                    f"recommendation without citations: option {option.option_id!r}"
                )
                raise RecommendationError(msg)
            if not option.supporting_rationale_refs:
                msg = f"missing rationale: option {option.option_id!r}"
                raise RecommendationError(msg)
            for key in option.supporting_report_refs:
                if key not in citations:
                    msg = f"broken report references: {key!r}"
                    raise RecommendationError(msg)

        score_ids: set[str] = set()
        for score in scores:
            if score.score_id in score_ids:
                msg = f"duplicate scores: id {score.score_id!r}"
                raise RecommendationError(msg)
            score_ids.add(score.score_id)
            if score.confidence_level is None:
                msg = f"invalid confidence: score {score.score_id!r} missing level"
                raise RecommendationError(msg)

        rationale_ids = {r.rationale_id for r in rationales}
        for option in options:
            for rid in option.supporting_rationale_refs:
                if rid not in rationale_ids:
                    msg = f"broken rationale references: {rid!r}"
                    raise RecommendationError(msg)
            if option.confidence_reference not in score_ids:
                msg = (
                    f"invalid confidence: option {option.option_id!r} "
                    f"references missing score"
                )
                raise RecommendationError(msg)

        for conflict in conflicts:
            for oid in conflict.option_refs:
                if oid not in option_ids:
                    msg = f"orphan conflicts: conflict references missing option {oid!r}"
                    raise RecommendationError(msg)
            for key in conflict.report_refs:
                if key not in citations:
                    msg = f"broken report references: conflict citation {key!r}"
                    raise RecommendationError(msg)
