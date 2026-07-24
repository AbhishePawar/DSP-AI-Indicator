"""Recommendation Assembler — construction / citation orchestration only (G1.1).

Builds immutable RecommendationProfile (+ structural RecommendationReport skeleton)
from upstream report citations. Never generates options, scores, rationales,
conflicts, or recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError

from recommendation.enums import AssemblyStatus
from recommendation.exceptions import RecommendationError
from recommendation.models import (
    RecommendationIdentity,
    RecommendationProfile,
    RecommendationReport,
    RecommendationSummary,
)
from recommendation.refs import (
    ComparisonReference,
    DecisionReference,
    PortfolioReference,
    QuantitativeRiskReference,
    ResearchReference,
    RiskReference,
)

__all__ = [
    "AssemblyContext",
    "AssemblyResult",
    "RecommendationAssembler",
]


@dataclass(frozen=True, slots=True)
class AssemblyContext:
    """Inputs for deterministic RecommendationProfile construction."""

    identity: RecommendationIdentity
    decision_refs: tuple[DecisionReference, ...]
    comparison_refs: tuple[ComparisonReference, ...]
    portfolio_ref: PortfolioReference
    risk_refs: tuple[RiskReference, ...]
    research_refs: tuple[ResearchReference, ...]
    quantitative_risk_refs: tuple[QuantitativeRiskReference, ...]
    as_of: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.identity is None:
            msg = "identity is required"
            raise ValidationError(msg)
        if self.portfolio_ref is None:
            msg = "portfolio_ref is required"
            raise ValidationError(msg)
        object.__setattr__(self, "decision_refs", tuple(self.decision_refs))
        object.__setattr__(self, "comparison_refs", tuple(self.comparison_refs))
        object.__setattr__(self, "risk_refs", tuple(self.risk_refs))
        object.__setattr__(self, "research_refs", tuple(self.research_refs))
        object.__setattr__(
            self, "quantitative_risk_refs", tuple(self.quantitative_risk_refs)
        )
        as_of = None if self.as_of is None else self.as_of.strip() or None
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(
            self, "notes", tuple(n.strip() for n in self.notes if n.strip())
        )


@dataclass(frozen=True, slots=True)
class AssemblyResult:
    """Assembler output — structural profile / report skeleton only."""

    profile: RecommendationProfile
    report: RecommendationReport
    status: AssemblyStatus
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", tuple(self.warnings))


class RecommendationAssembler:
    """Canonical constructor for immutable RecommendationProfile skeletons.

    Construction and reference validation only — no recommendation synthesis.
    """

    def validate_inputs(self, context: AssemblyContext) -> None:
        """Reject invalid assembly inputs before construction."""
        if context.identity is None:
            msg = "missing RecommendationIdentity"
            raise RecommendationError(msg)
        if not context.identity.recommendation_id:
            msg = "missing RecommendationIdentity: empty recommendation_id"
            raise RecommendationError(msg)
        if not context.identity.recommendation_name:
            msg = "missing RecommendationIdentity: empty recommendation_name"
            raise RecommendationError(msg)

        if not context.decision_refs:
            msg = "missing Decision reference: at least one DecisionReference required"
            raise RecommendationError(msg)
        if not context.comparison_refs:
            msg = (
                "missing Comparison reference: at least one ComparisonReference required"
            )
            raise RecommendationError(msg)
        if context.portfolio_ref is None:
            msg = "missing Portfolio reference: PortfolioReference required"
            raise RecommendationError(msg)
        if not context.risk_refs:
            msg = "missing Risk reference: at least one RiskReference required"
            raise RecommendationError(msg)
        if not context.research_refs:
            msg = "missing Research reference: at least one ResearchReference required"
            raise RecommendationError(msg)
        if not context.quantitative_risk_refs:
            msg = (
                "missing Quantitative Risk reference: at least one "
                "QuantitativeRiskReference required"
            )
            raise RecommendationError(msg)

        seen_decision_symbol: set[str] = set()
        seen_decision_digest: set[str] = set()
        for ref in context.decision_refs:
            if ref is None or not ref.digest or len(ref.digest) < 8:
                msg = "broken references: DecisionReference digest invalid"
                raise RecommendationError(msg)
            if not ref.instrument_symbol:
                msg = "broken references: DecisionReference missing symbol"
                raise RecommendationError(msg)
            if ref.instrument_symbol in seen_decision_symbol:
                msg = (
                    "duplicate report references: DecisionReference for "
                    f"{ref.instrument_symbol!r}"
                )
                raise RecommendationError(msg)
            if ref.digest in seen_decision_digest:
                msg = (
                    f"duplicate report references: DecisionReference digest "
                    f"{ref.digest!r}"
                )
                raise RecommendationError(msg)
            seen_decision_symbol.add(ref.instrument_symbol)
            seen_decision_digest.add(ref.digest)

        seen_comp: set[str] = set()
        for ref in context.comparison_refs:
            if ref is None or not ref.digest or len(ref.digest) < 8:
                msg = "broken references: ComparisonReference digest invalid"
                raise RecommendationError(msg)
            if ref.digest in seen_comp:
                msg = (
                    f"duplicate report references: ComparisonReference {ref.digest!r}"
                )
                raise RecommendationError(msg)
            seen_comp.add(ref.digest)

        if not context.portfolio_ref.portfolio_id:
            msg = "broken references: PortfolioReference portfolio_id invalid"
            raise RecommendationError(msg)

        seen_risk: set[str] = set()
        for ref in context.risk_refs:
            if ref is None or not ref.risk_id:
                msg = "broken references: RiskReference invalid"
                raise RecommendationError(msg)
            if ref.risk_id in seen_risk:
                msg = f"duplicate report references: RiskReference {ref.risk_id!r}"
                raise RecommendationError(msg)
            seen_risk.add(ref.risk_id)

        seen_research: set[str] = set()
        for ref in context.research_refs:
            if ref is None or not ref.research_id:
                msg = "broken references: ResearchReference invalid"
                raise RecommendationError(msg)
            if ref.research_id in seen_research:
                msg = (
                    f"duplicate report references: ResearchReference "
                    f"{ref.research_id!r}"
                )
                raise RecommendationError(msg)
            seen_research.add(ref.research_id)

        seen_quant: set[str] = set()
        for ref in context.quantitative_risk_refs:
            if ref is None or not ref.quantitative_risk_id:
                msg = "broken references: QuantitativeRiskReference invalid"
                raise RecommendationError(msg)
            if ref.quantitative_risk_id in seen_quant:
                msg = (
                    "duplicate report references: QuantitativeRiskReference "
                    f"{ref.quantitative_risk_id!r}"
                )
                raise RecommendationError(msg)
            seen_quant.add(ref.quantitative_risk_id)

        # Foreign ownership: DecisionPack symbols must be consistent within assembly
        # when a single-instrument recommendation is intended (all symbols equal).
        symbols = {ref.instrument_symbol for ref in context.decision_refs}
        if len(symbols) > 1:
            msg = (
                "foreign ownership: DecisionReference instrument symbols disagree "
                f"{sorted(symbols)}"
            )
            raise RecommendationError(msg)

    def assemble(self, context: AssemblyContext) -> AssemblyResult:
        """Construct immutable profile and empty recommendation report skeleton."""
        self.validate_inputs(context)

        as_of = context.as_of or "unknown"
        warnings: list[str] = []
        if context.as_of is None:
            warnings.append("as_of missing; report uses placeholder 'unknown'.")

        summary = RecommendationSummary(
            option_count=0,
            conflict_count=0,
            rationale_count=0,
            score_count=0,
            limitation_notes=(
                "Assembly skeleton only — options / scores / rationales / "
                "conflicts populated by Recommendation Engine (G1.2).",
                *context.notes,
            ),
        )

        profile = RecommendationProfile(
            identity=context.identity,
            decision_refs=context.decision_refs,
            comparison_refs=context.comparison_refs,
            portfolio_ref=context.portfolio_ref,
            risk_refs=context.risk_refs,
            research_refs=context.research_refs,
            quantitative_risk_refs=context.quantitative_risk_refs,
            options=(),
            scores=(),
            rationales=(),
            conflicts=(),
            summary=summary,
            notes=context.notes,
        )

        report = RecommendationReport(
            recommendation_id=context.identity.recommendation_id,
            summary=summary,
            as_of=as_of,
            options=(),
            scores=(),
            rationales=(),
            conflicts=(),
            decision_refs=context.decision_refs,
            comparison_refs=context.comparison_refs,
            portfolio_ref=context.portfolio_ref,
            risk_refs=context.risk_refs,
            research_refs=context.research_refs,
            quantitative_risk_refs=context.quantitative_risk_refs,
            limitations=(
                "RecommendationReport skeleton — no recommendation content yet.",
                *summary.limitation_notes,
            ),
        )

        status = (
            AssemblyStatus.PARTIAL if warnings else AssemblyStatus.COMPLETE
        )
        return AssemblyResult(
            profile=profile,
            report=report,
            status=status,
            warnings=tuple(warnings),
        )

    def assemble_many(
        self, contexts: tuple[AssemblyContext, ...]
    ) -> tuple[AssemblyResult, ...]:
        """Assemble many contexts; reject duplicate recommendation identities."""
        seen: set[str] = set()
        results: list[AssemblyResult] = []
        for context in contexts:
            rid = context.identity.recommendation_id
            if rid in seen:
                msg = f"duplicate identities: recommendation_id {rid!r}"
                raise RecommendationError(msg)
            seen.add(rid)
            results.append(self.assemble(context))
        return tuple(results)
