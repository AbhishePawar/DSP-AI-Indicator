"""Risk Assembler — construction / orchestration only (E1.1).

Builds immutable RiskProfile (+ structural RiskReport) from citations.
Never analyzes, evaluates coverage posture, scores, or recommends.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError
from industry import EvidenceBundleReference
from portfolio import ComparisonReportReference, DecisionPackReference

from risk.enums import RiskAssemblyStatus
from risk.exceptions import RiskError
from risk.models import (
    RiskConstraint,
    RiskIdentity,
    RiskProfile,
    RiskReport,
    RiskSummary,
)
from risk.refs import MonitoringReference, PortfolioReference

__all__ = [
    "RiskAssembler",
    "RiskAssemblyContext",
    "RiskAssemblyResult",
]


@dataclass(frozen=True, slots=True)
class RiskAssemblyContext:
    """Inputs for deterministic RiskProfile construction."""

    identity: RiskIdentity
    portfolio_ref: PortfolioReference
    monitoring_ref: MonitoringReference | None = None
    decision_pack_refs: tuple[DecisionPackReference, ...] = ()
    evidence_bundle_refs: tuple[EvidenceBundleReference, ...] = ()
    comparison_report_refs: tuple[ComparisonReportReference, ...] = ()
    constraints: tuple[RiskConstraint, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.identity is None:
            msg = "identity is required"
            raise ValidationError(msg)
        if self.portfolio_ref is None:
            msg = "portfolio_ref is required"
            raise ValidationError(msg)
        object.__setattr__(
            self, "decision_pack_refs", tuple(self.decision_pack_refs)
        )
        object.__setattr__(
            self, "evidence_bundle_refs", tuple(self.evidence_bundle_refs)
        )
        object.__setattr__(
            self, "comparison_report_refs", tuple(self.comparison_report_refs)
        )
        object.__setattr__(self, "constraints", tuple(self.constraints))
        object.__setattr__(
            self, "notes", tuple(n.strip() for n in self.notes if n.strip())
        )


@dataclass(frozen=True, slots=True)
class RiskAssemblyResult:
    """Assembler output — structural RiskProfile / RiskReport only."""

    profile: RiskProfile
    report: RiskReport
    status: RiskAssemblyStatus
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", tuple(self.warnings))


class RiskAssembler:
    """Canonical constructor for immutable RiskProfile objects.

    Construction and validation only — no qualitative analysis.
    """

    def validate_inputs(self, context: RiskAssemblyContext) -> None:
        """Reject invalid assembly inputs before construction."""
        if context.identity is None:
            msg = "invalid identities: RiskIdentity is required"
            raise RiskError(msg)
        if not context.identity.risk_id:
            msg = "invalid identities: empty risk_id"
            raise RiskError(msg)
        if not context.identity.risk_name:
            msg = "invalid identities: empty risk_name"
            raise RiskError(msg)
        if context.portfolio_ref is None:
            msg = "broken citation references: portfolio_ref is required"
            raise RiskError(msg)
        if not context.portfolio_ref.portfolio_id:
            msg = "broken citation references: empty portfolio_id"
            raise RiskError(msg)

        if context.monitoring_ref is not None:
            if (
                context.monitoring_ref.portfolio_id
                != context.portfolio_ref.portfolio_id
            ):
                msg = (
                    "foreign Monitoring ownership: monitoring portfolio_id "
                    f"{context.monitoring_ref.portfolio_id!r} does not match "
                    f"{context.portfolio_ref.portfolio_id!r}"
                )
                raise RiskError(msg)

        seen_pack: set[str] = set()
        for ref in context.decision_pack_refs:
            if ref is None or not ref.digest or len(ref.digest) < 8:
                msg = "broken citation references: DecisionPack digest invalid"
                raise RiskError(msg)
            if not ref.instrument_symbol:
                msg = "broken citation references: DecisionPack missing symbol"
                raise RiskError(msg)
            if ref.instrument_symbol in seen_pack:
                msg = (
                    f"duplicate references: DecisionPack for "
                    f"{ref.instrument_symbol!r}"
                )
                raise RiskError(msg)
            seen_pack.add(ref.instrument_symbol)

        seen_ev_id: set[str] = set()
        seen_ev_key: set[tuple[str, str]] = set()
        for ref in context.evidence_bundle_refs:
            if ref is None or not ref.bundle_id or not ref.digest:
                msg = "broken citation references: EvidenceBundle invalid"
                raise RiskError(msg)
            if ref.bundle_id in seen_ev_id:
                msg = f"duplicate references: EvidenceBundle {ref.bundle_id!r}"
                raise RiskError(msg)
            key = (ref.instrument_key, ref.digest)
            if key in seen_ev_key:
                msg = (
                    f"duplicate references: EvidenceBundle for "
                    f"{ref.instrument_key!r}"
                )
                raise RiskError(msg)
            seen_ev_id.add(ref.bundle_id)
            seen_ev_key.add(key)

        seen_comp: set[str] = set()
        for ref in context.comparison_report_refs:
            if ref is None or not ref.digest or len(ref.digest) < 8:
                msg = "broken citation references: ComparisonReport digest invalid"
                raise RiskError(msg)
            if ref.digest in seen_comp:
                msg = f"duplicate references: ComparisonReport {ref.digest!r}"
                raise RiskError(msg)
            seen_comp.add(ref.digest)

        seen_constraints: set[str] = set()
        for constraint in context.constraints:
            if constraint.id in seen_constraints:
                msg = f"duplicate references: constraint {constraint.id!r}"
                raise RiskError(msg)
            seen_constraints.add(constraint.id)

    def assemble(self, context: RiskAssemblyContext) -> RiskAssemblyResult:
        """Construct immutable RiskProfile and structural RiskReport."""
        self.validate_inputs(context)

        profile = RiskProfile(
            identity=context.identity,
            portfolio_ref=context.portfolio_ref,
            monitoring_ref=context.monitoring_ref,
            decision_pack_refs=context.decision_pack_refs,
            evidence_bundle_refs=context.evidence_bundle_refs,
            comparison_report_refs=context.comparison_report_refs,
            constraints=context.constraints,
            assessments=(),
            notes=context.notes,
        )

        report = RiskReport(
            risk_id=context.identity.risk_id,
            portfolio_id=context.portfolio_ref.portfolio_id,
            summary=RiskSummary(
                observation_count=0,
                descriptor_count=0,
                limitation_notes=(
                    "Structural RiskReport only — no qualitative analysis.",
                ),
            ),
            observations=(),
            descriptors=(),
            coverage=(),
            assessment_id=None,
            decision_pack_refs=context.decision_pack_refs,
            evidence_bundle_refs=context.evidence_bundle_refs,
            comparison_report_refs=context.comparison_report_refs,
            limitations=(
                "Assembled structure only — no observations, descriptors, "
                "or assessments.",
            ),
        )

        warnings: list[str] = []
        if context.monitoring_ref is None:
            warnings.append("Optional MonitoringReference was not supplied.")
            status = RiskAssemblyStatus.PARTIAL
        else:
            status = RiskAssemblyStatus.COMPLETE

        return RiskAssemblyResult(
            profile=profile,
            report=report,
            status=status,
            warnings=tuple(warnings),
        )

    def assemble_many(
        self, contexts: tuple[RiskAssemblyContext, ...]
    ) -> tuple[RiskAssemblyResult, ...]:
        """Assemble many profiles; reject duplicate risk_id / report pairs."""
        seen_ids: set[str] = set()
        results: list[RiskAssemblyResult] = []
        for ctx in contexts:
            if ctx.identity.risk_id in seen_ids:
                msg = (
                    f"duplicate reports: risk_id {ctx.identity.risk_id!r} "
                    f"appears more than once in assemble_many"
                )
                raise RiskError(msg)
            seen_ids.add(ctx.identity.risk_id)
            results.append(self.assemble(ctx))
        return tuple(results)
