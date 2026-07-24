"""Research Assembler — construction / orchestration only (F1.1).

Builds immutable ResearchProfile (+ structural ResearchReport) from citations.
Never synthesizes insights, detects conflicts/gaps, prioritizes, or recommends.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError

from research.enums import ResearchAssemblyStatus, ResearchCoverageStatus
from research.exceptions import ResearchError
from research.models import (
    ResearchAgenda,
    ResearchCoverage,
    ResearchIdentity,
    ResearchProfile,
    ResearchReport,
    ResearchSummary,
)
from research.refs import (
    ComparisonReference,
    DecisionReference,
    EvidenceReference,
    IntegratedRiskReference,
    MonitoringReference,
    PortfolioReference,
    RiskReference,
)

__all__ = [
    "ResearchAssembler",
    "ResearchAssemblyContext",
    "ResearchAssemblyResult",
]


@dataclass(frozen=True, slots=True)
class ResearchAssemblyContext:
    """Inputs for deterministic ResearchProfile construction."""

    identity: ResearchIdentity
    evidence_refs: tuple[EvidenceReference, ...]
    decision_refs: tuple[DecisionReference, ...] = ()
    comparison_refs: tuple[ComparisonReference, ...] = ()
    portfolio_ref: PortfolioReference | None = None
    monitoring_ref: MonitoringReference | None = None
    risk_refs: tuple[RiskReference, ...] = ()
    integrated_risk_refs: tuple[IntegratedRiskReference, ...] = ()
    as_of: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.identity is None:
            msg = "identity is required"
            raise ValidationError(msg)
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "decision_refs", tuple(self.decision_refs))
        object.__setattr__(self, "comparison_refs", tuple(self.comparison_refs))
        object.__setattr__(self, "risk_refs", tuple(self.risk_refs))
        object.__setattr__(
            self, "integrated_risk_refs", tuple(self.integrated_risk_refs)
        )
        as_of = None if self.as_of is None else self.as_of.strip() or None
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(
            self, "notes", tuple(n.strip() for n in self.notes if n.strip())
        )


@dataclass(frozen=True, slots=True)
class ResearchAssemblyResult:
    """Assembler output — structural ResearchProfile / ResearchReport only."""

    profile: ResearchProfile
    report: ResearchReport
    status: ResearchAssemblyStatus
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", tuple(self.warnings))


class ResearchAssembler:
    """Canonical constructor for immutable ResearchProfile objects.

    Construction and validation only — no synthesis.
    """

    def validate_inputs(self, context: ResearchAssemblyContext) -> None:
        """Reject invalid assembly inputs before construction."""
        if context.identity is None:
            msg = "missing ResearchIdentity"
            raise ResearchError(msg)
        if not context.identity.research_id:
            msg = "missing ResearchIdentity: empty research_id"
            raise ResearchError(msg)
        if not context.identity.research_name:
            msg = "missing ResearchIdentity: empty research_name"
            raise ResearchError(msg)

        if not context.evidence_refs:
            msg = "missing EvidenceReference: at least one evidence citation required"
            raise ResearchError(msg)

        if context.monitoring_ref is not None and context.portfolio_ref is not None:
            if (
                context.monitoring_ref.portfolio_id
                != context.portfolio_ref.portfolio_id
            ):
                msg = (
                    "foreign ownership: monitoring portfolio_id "
                    f"{context.monitoring_ref.portfolio_id!r} does not match "
                    f"{context.portfolio_ref.portfolio_id!r}"
                )
                raise ResearchError(msg)

        if context.monitoring_ref is not None and context.portfolio_ref is None:
            msg = (
                "broken references: MonitoringReference requires PortfolioReference"
            )
            raise ResearchError(msg)

        seen_pack: set[str] = set()
        for ref in context.decision_refs:
            if ref is None or not ref.digest or len(ref.digest) < 8:
                msg = "broken references: DecisionReference digest invalid"
                raise ResearchError(msg)
            if not ref.instrument_symbol:
                msg = "broken references: DecisionReference missing symbol"
                raise ResearchError(msg)
            if ref.instrument_symbol in seen_pack:
                msg = (
                    f"duplicate references: DecisionReference for "
                    f"{ref.instrument_symbol!r}"
                )
                raise ResearchError(msg)
            seen_pack.add(ref.instrument_symbol)

        seen_ev_id: set[str] = set()
        seen_ev_key: set[tuple[str, str]] = set()
        for ref in context.evidence_refs:
            if ref is None or not ref.bundle_id or not ref.digest:
                msg = "broken references: EvidenceReference invalid"
                raise ResearchError(msg)
            if len(ref.digest) < 8:
                msg = "broken references: EvidenceReference digest invalid"
                raise ResearchError(msg)
            if ref.bundle_id in seen_ev_id:
                msg = f"duplicate references: EvidenceReference {ref.bundle_id!r}"
                raise ResearchError(msg)
            key = (ref.bundle_id, ref.digest)
            if key in seen_ev_key:
                msg = (
                    f"duplicate citations: EvidenceReference for "
                    f"{ref.bundle_id!r}"
                )
                raise ResearchError(msg)
            seen_ev_id.add(ref.bundle_id)
            seen_ev_key.add(key)

        seen_comp: set[str] = set()
        for ref in context.comparison_refs:
            if ref is None or not ref.digest or len(ref.digest) < 8:
                msg = "broken references: ComparisonReference digest invalid"
                raise ResearchError(msg)
            if ref.digest in seen_comp:
                msg = f"duplicate references: ComparisonReference {ref.digest!r}"
                raise ResearchError(msg)
            seen_comp.add(ref.digest)

        seen_risk: set[str] = set()
        for ref in context.risk_refs:
            if ref is None or not ref.risk_id:
                msg = "broken references: RiskReference invalid"
                raise ResearchError(msg)
            if ref.risk_id in seen_risk:
                msg = f"duplicate references: RiskReference {ref.risk_id!r}"
                raise ResearchError(msg)
            seen_risk.add(ref.risk_id)

        seen_integrated: set[str] = set()
        for ref in context.integrated_risk_refs:
            if ref is None or not ref.risk_id:
                msg = "broken references: IntegratedRiskReference invalid"
                raise ResearchError(msg)
            if ref.risk_id in seen_integrated:
                msg = (
                    f"duplicate references: IntegratedRiskReference "
                    f"{ref.risk_id!r}"
                )
                raise ResearchError(msg)
            seen_integrated.add(ref.risk_id)

    def assemble(self, context: ResearchAssemblyContext) -> ResearchAssemblyResult:
        """Construct immutable ResearchProfile and structural ResearchReport."""
        try:
            self.validate_inputs(context)
        except ResearchError:
            raise
        except ValidationError as exc:
            msg = f"FAILED assembly: {exc}"
            raise ResearchError(msg) from exc

        coverage = self._initial_coverage(context)
        summary = ResearchSummary(
            observation_count=0,
            insight_count=0,
            conflict_count=0,
            gap_count=0,
            agenda_item_count=0,
            coverage_notes=tuple(
                f"{c.dimension}: {c.status.value}" for c in coverage
            ),
            limitation_notes=(
                "Structural ResearchSummary only — no synthesis performed.",
            ),
        )
        agenda = ResearchAgenda(
            agenda_id=f"{context.identity.research_id}.agenda",
            priorities=(),
            notes=("Empty agenda — synthesis deferred to ResearchSynthesizer.",),
        )

        profile = ResearchProfile(
            identity=context.identity,
            portfolio_ref=context.portfolio_ref,
            monitoring_ref=context.monitoring_ref,
            decision_refs=context.decision_refs,
            evidence_refs=context.evidence_refs,
            comparison_refs=context.comparison_refs,
            risk_refs=context.risk_refs,
            integrated_risk_refs=context.integrated_risk_refs,
            observations=(),
            insights=(),
            conflicts=(),
            gaps=(),
            agenda=agenda,
            coverage=coverage,
            summary=summary,
            notes=context.notes,
        )

        as_of = (
            context.as_of
            or context.identity.created_at
            or "assembled"
        )
        report = ResearchReport(
            research_id=context.identity.research_id,
            summary=summary,
            as_of=as_of,
            observations=(),
            insights=(),
            conflicts=(),
            gaps=(),
            agenda=agenda,
            coverage=coverage,
            decision_refs=context.decision_refs,
            evidence_refs=context.evidence_refs,
            comparison_refs=context.comparison_refs,
            portfolio_ref=context.portfolio_ref,
            monitoring_ref=context.monitoring_ref,
            risk_refs=context.risk_refs,
            integrated_risk_refs=context.integrated_risk_refs,
            limitations=(
                "Assembled structure only — no insights, conflicts, gaps, "
                "or priorities.",
            ),
        )

        status, warnings = self._status_and_warnings(context)
        return ResearchAssemblyResult(
            profile=profile,
            report=report,
            status=status,
            warnings=warnings,
        )

    def assemble_many(
        self, contexts: tuple[ResearchAssemblyContext, ...]
    ) -> tuple[ResearchAssemblyResult, ...]:
        """Assemble many profiles; reject duplicate research_id pairs."""
        seen_ids: set[str] = set()
        results: list[ResearchAssemblyResult] = []
        for ctx in contexts:
            if ctx.identity.research_id in seen_ids:
                msg = (
                    f"duplicate citations: research_id "
                    f"{ctx.identity.research_id!r} appears more than once "
                    f"in assemble_many"
                )
                raise ResearchError(msg)
            seen_ids.add(ctx.identity.research_id)
            results.append(self.assemble(ctx))
        return tuple(results)

    def _initial_coverage(
        self, context: ResearchAssemblyContext
    ) -> tuple[ResearchCoverage, ...]:
        """Structural coverage stubs from citation presence — not interpretation."""

        def row(dimension: str, present: bool) -> ResearchCoverage:
            if present:
                return ResearchCoverage(
                    dimension=dimension,
                    status=ResearchCoverageStatus.PARTIAL,
                    label=f"{dimension.replace('_', ' ').capitalize()} citations attached.",
                )
            return ResearchCoverage(
                dimension=dimension,
                status=ResearchCoverageStatus.INSUFFICIENT,
                label=f"{dimension.replace('_', ' ').capitalize()} citations absent.",
            )

        return (
            row("decision", bool(context.decision_refs)),
            row("evidence", bool(context.evidence_refs)),
            row("comparison", bool(context.comparison_refs)),
            row("portfolio", context.portfolio_ref is not None),
            row("monitoring", context.monitoring_ref is not None),
            row(
                "risk",
                bool(context.risk_refs) or bool(context.integrated_risk_refs),
            ),
        )

    def _status_and_warnings(
        self, context: ResearchAssemblyContext
    ) -> tuple[ResearchAssemblyStatus, tuple[str, ...]]:
        warnings: list[str] = []
        has_portfolio = context.portfolio_ref is not None
        has_monitoring = context.monitoring_ref is not None
        has_decision = bool(context.decision_refs)
        has_comparison = bool(context.comparison_refs)
        has_risk = bool(context.risk_refs) or bool(context.integrated_risk_refs)

        optional_present = (
            has_portfolio,
            has_monitoring,
            has_decision,
            has_comparison,
            has_risk,
        )
        if all(optional_present):
            status = ResearchAssemblyStatus.COMPLETE
        elif not any(optional_present):
            status = ResearchAssemblyStatus.EMPTY
            warnings.append(
                "Only EvidenceReference citations present — structural shell."
            )
        else:
            status = ResearchAssemblyStatus.PARTIAL
            if not has_portfolio:
                warnings.append("Optional PortfolioReference was not supplied.")
            if not has_monitoring:
                warnings.append("Optional MonitoringReference was not supplied.")
            if not has_decision:
                warnings.append("Optional DecisionReference citations absent.")
            if not has_comparison:
                warnings.append("Optional ComparisonReference citations absent.")
            if not has_risk:
                warnings.append("Optional Risk citations absent.")

        warnings.append(
            "Assembler construction only — synthesis deferred to F1.2."
        )
        return status, tuple(warnings)
