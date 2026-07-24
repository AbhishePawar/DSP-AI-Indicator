"""Qualitative Comparison Engine — policy consumer, not policy owner."""

from __future__ import annotations

from decision_intelligence import DecisionPack
from industry import (
    ComparisonDimension,
    EligibilityOptions,
    EvidenceBundle,
    GroupEligibilityStatus,
    IndustryMethodology,
    IndustryMethodologyRegistry,
    PeerEligibilityEvaluator,
)
from universe import summarize_decision_pack

from comparison.enums import ComparisonStatus
from comparison.exceptions import ComparisonError
from comparison.evidence_integration import (
    build_comparison_evidence_summary,
    build_evidence_backed_observations,
    build_evidence_limitations,
    validate_evidence_bundles_for_comparison,
)
from comparison.models import (
    ComparisonEvidenceSummary,
    ComparisonExplanation,
    ComparisonLimitation,
    ComparisonReport,
    ComparisonRequest,
    ComparisonResult,
)
from comparison.observations import (
    build_decision_context,
    build_dimension_results,
    build_limitations,
    build_pair_observations,
    build_research_priorities,
    build_robustness_context,
    build_shared_observations,
    build_valuation_context,
)

__all__ = ["QualitativeComparisonEngine"]


class QualitativeComparisonEngine:
    """Compare DecisionPacks qualitatively after peer-eligibility gating.

    Owns no IndustryMethodology. Does not score or rank.
    """

    def __init__(
        self,
        *,
        evaluator: PeerEligibilityEvaluator,
        methodologies: IndustryMethodologyRegistry,
    ) -> None:
        self._evaluator = evaluator
        self._methodologies = methodologies

    def compare(self, request: ComparisonRequest) -> ComparisonResult:
        packs = request.packs
        options = request.eligibility_options
        symbols = tuple(p.recommendation.instrument.symbol for p in packs)
        pack_by_symbol = {
            p.recommendation.instrument.symbol: p for p in packs
        }

        # --- Entry validation: resolution + eligibility ---
        resolution_errors: list[str] = []
        resolutions = {}
        for symbol in symbols:
            try:
                resolutions[symbol] = self._evaluator.resolve(symbol)
            except Exception as exc:  # IndustryError
                resolution_errors.append(f"{symbol}: {exc}")

        if resolution_errors:
            return self._refuse(
                scope_notes=(
                    "Instrument or methodology resolution failed before comparison.",
                ),
                exclusion_reasons=tuple(resolution_errors),
                excluded=symbols,
                options=options,
                explanation=ComparisonExplanation(
                    summary=(
                        "Comparison refused: one or more instruments could not "
                        "be resolved to IndustryMethodology and peer policy."
                    ),
                    detail="; ".join(resolution_errors),
                ),
            )

        group = self._evaluator.evaluate_group(symbols, options=options)
        comparable_pairs = [
            (p.left_key, p.right_key)
            for p in group.pair_results
            if p.comparable
        ]

        if not comparable_pairs:
            return self._refuse(
                scope_notes=(
                    "Peer eligibility produced no comparable pairs.",
                ),
                exclusion_reasons=group.exclusions,
                excluded=symbols,
                options=options,
                eligibility_status=group.status,
                explanation=ComparisonExplanation(
                    summary=(
                        "Comparison refused: peer eligibility does not permit "
                        "comparing these instruments under current options."
                    ),
                    detail="; ".join(group.exclusions) or None,
                ),
            )

        included = tuple(
            sorted(
                {
                    s
                    for pair in comparable_pairs
                    for s in pair
                }
            )
        )
        excluded = tuple(s for s in symbols if s not in set(included))
        filtered_exclusions = tuple(
            e
            for e in group.exclusions
            if any(sym in e for sym in excluded)
        )
        if excluded and not filtered_exclusions:
            filtered_exclusions = group.exclusions

        # Single methodology among included
        method_ids = {
            resolutions[s].methodology_id for s in included
        }
        if len(method_ids) != 1:
            return self._refuse(
                scope_notes=(
                    "Included peers resolve to heterogeneous methodologies.",
                ),
                exclusion_reasons=(
                    "Qualitative comparison requires a single IndustryMethodology "
                    f"among included peers; found {sorted(method_ids)}.",
                    *filtered_exclusions,
                ),
                excluded=symbols,
                options=options,
                eligibility_status=group.status,
                explanation=ComparisonExplanation(
                    summary=(
                        "Comparison refused: related peers with distinct "
                        "methodologies are not compared as one group in C2.5."
                    ),
                ),
            )

        methodology_id = next(iter(method_ids))
        sample = resolutions[included[0]]
        methodology = self._methodologies.get(
            methodology_id, version=sample.methodology_version
        )
        dimensions = self._dimensions_for(methodology)

        included_packs = tuple(pack_by_symbol[s] for s in included)
        summaries = tuple(summarize_decision_pack(p) for p in included_packs)

        shared = build_shared_observations(summaries)
        pair_notes: list = []
        summary_by = {s.instrument.symbol: s for s in summaries}
        for left_key, right_key in comparable_pairs:
            if left_key in summary_by and right_key in summary_by:
                pair_notes.extend(
                    build_pair_observations(
                        summary_by[left_key], summary_by[right_key]
                    )
                )
        pair_obs = tuple(pair_notes)

        decision_ctx = build_decision_context(summaries)
        valuation_ctx = build_valuation_context(summaries)
        robustness_ctx = build_robustness_context(summaries)
        dimension_results = build_dimension_results(
            dimensions, shared, pair_obs
        )

        status = (
            ComparisonStatus.COMPLETE
            if not excluded and group.status is GroupEligibilityStatus.ELIGIBLE
            else ComparisonStatus.DEGRADED
        )

        methodology_gaps: list[str] = []
        assembled = None
        try:
            assembled = self._methodologies.assemble(methodology)
            if assembled.valuation.requires_engine_extension:
                methodology_gaps.append(
                    "Valuation methods still require engine extension: "
                    + ", ".join(assembled.valuation.requires_engine_extension)
                )
        except Exception as exc:
            methodology_gaps.append(f"Could not assemble methodology: {exc}")

        limitations = build_limitations(
            summaries,
            excluded=excluded,
            exclusion_reasons=filtered_exclusions,
            methodology_gaps=tuple(methodology_gaps),
            degraded=status is ComparisonStatus.DEGRADED,
        )

        relevant_bundles = tuple(
            b
            for b in request.evidence_bundles
            if b.metadata.instrument_key in set(included)
        )
        for bundle in request.evidence_bundles:
            if bundle.metadata.instrument_key not in set(included):
                msg = (
                    f"evidence bundle instrument "
                    f"{bundle.metadata.instrument_key!r} is not among "
                    f"included comparison peers {list(included)!r}"
                )
                raise ComparisonError(msg)
        if relevant_bundles:
            validate_evidence_bundles_for_comparison(
                relevant_bundles,
                packs=included_packs,
                methodology_id=methodology.id,
                methodology_version=methodology.version,
                included_symbols=included,
            )

        evidence_summary = build_comparison_evidence_summary(
            relevant_bundles,
            included_symbols=included,
            methodology_id=methodology.id,
        )
        evidence_observations = build_evidence_backed_observations(
            relevant_bundles, included_symbols=included
        )
        evidence_limitations = build_evidence_limitations(
            relevant_bundles, included_symbols=included
        )
        limitations = tuple((*limitations, *evidence_limitations))

        priorities = build_research_priorities(
            limitations, dimensions, dimension_results
        )

        scope = [
            f"Qualitative comparison of {len(included)} companies "
            f"({', '.join(included)}).",
            f"Methodology {methodology.id}@{methodology.version} "
            f"(industry {methodology.industry_id}).",
            "No scores, rankings, or league tables are produced.",
        ]
        if excluded:
            scope.append(
                f"Excluded from comparison: {', '.join(excluded)}."
            )
        if evidence_summary.attached:
            scope.append(
                f"Industry Evidence Bundles cited for "
                f"{len(evidence_summary.covered_symbols)} peer(s); "
                f"availability={evidence_summary.availability}."
            )
        else:
            scope.append(
                "Industry Evidence Bundles were not supplied "
                "(DecisionPack-only path)."
            )

        explanation = ComparisonExplanation(
            summary=(
                f"Qualitative peer comparison {status.value}: "
                f"{len(included)} included, {len(excluded)} excluded."
            ),
            detail=(
                "Observations describe Decision Pack differences along "
                "methodology-declared dimensions and may cite Industry "
                "Evidence Bundle observations when supplied. They do not "
                "imply a preferred investment."
            ),
        )

        report = ComparisonReport(
            status=status,
            scope_notes=tuple(scope),
            methodology_id=methodology.id,
            methodology_version=methodology.version,
            industry_id=methodology.industry_id,
            included_symbols=included,
            excluded_symbols=excluded,
            exclusion_reasons=filtered_exclusions,
            eligibility_group_status=group.status,
            dimension_results=dimension_results,
            shared_observations=shared,
            pair_observations=pair_obs,
            decision_context=decision_ctx,
            valuation_context=valuation_ctx,
            robustness_context=robustness_ctx,
            limitations=limitations,
            research_priorities=priorities,
            explanation=explanation,
            evidence_summary=evidence_summary,
            evidence_observations=evidence_observations,
            evidence_limitations=evidence_limitations,
        )
        return ComparisonResult(status=status, report=report)

    def compare_packs(
        self,
        packs: tuple[DecisionPack, ...] | list[DecisionPack],
        *,
        eligibility_options: EligibilityOptions | None = None,
        evidence_bundles: tuple[EvidenceBundle, ...] = (),
    ) -> ComparisonResult:
        return self.compare(
            ComparisonRequest(
                packs=tuple(packs),
                eligibility_options=eligibility_options or EligibilityOptions(),
                evidence_bundles=evidence_bundles,
            )
        )

    def _dimensions_for(
        self, methodology: IndustryMethodology
    ) -> tuple[ComparisonDimension, ...]:
        if methodology.dimensions is not None:
            return methodology.dimensions
        # Fall through to assembled defaults when methodology omits dimensions
        try:
            assembled = self._methodologies.assemble(methodology)
            return assembled.dimensions
        except Exception:
            return (
                ComparisonDimension.QUALITY,
                ComparisonDimension.VALUATION,
                ComparisonDimension.DECISION_ROBUSTNESS,
            )

    def _refuse(
        self,
        *,
        scope_notes: tuple[str, ...],
        exclusion_reasons: tuple[str, ...],
        excluded: tuple[str, ...],
        options: EligibilityOptions,
        explanation: ComparisonExplanation,
        eligibility_status: GroupEligibilityStatus | None = None,
    ) -> ComparisonResult:
        limitations = (
            ComparisonLimitation(
                code="refused",
                message=explanation.summary,
                subjects=excluded,
            ),
            ComparisonLimitation(
                code="qualitative_only",
                message=(
                    "Even when comparison proceeds, DSP never scores or ranks."
                ),
            ),
            *(
                ComparisonLimitation(
                    code="exclusion",
                    message=reason,
                    subjects=excluded,
                )
                for reason in exclusion_reasons
            ),
        )
        report = ComparisonReport(
            status=ComparisonStatus.REFUSED,
            scope_notes=scope_notes,
            methodology_id=None,
            methodology_version=None,
            industry_id=None,
            included_symbols=(),
            excluded_symbols=excluded,
            exclusion_reasons=exclusion_reasons,
            eligibility_group_status=eligibility_status,
            dimension_results=(),
            shared_observations=(),
            pair_observations=(),
            decision_context=(),
            valuation_context=(),
            robustness_context=(),
            limitations=limitations,
            research_priorities=tuple(exclusion_reasons),
            explanation=explanation,
            evidence_summary=ComparisonEvidenceSummary.not_supplied(),
            evidence_observations=(),
            evidence_limitations=(),
        )
        return ComparisonResult(status=ComparisonStatus.REFUSED, report=report)
