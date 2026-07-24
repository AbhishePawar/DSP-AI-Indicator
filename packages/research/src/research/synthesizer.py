"""Research Synthesizer — qualitative synthesis only (F1.2).

Consumes assembled ResearchProfile / citations.
Emits observations, insights, gaps, conflicts, agenda, updated report.
Never re-analyzes Evidence, recalculates Risk, recomputes Portfolio, or recommends trades.
"""

from __future__ import annotations

from dataclasses import dataclass

from research.enums import (
    ResearchConflictSeverity,
    ResearchCoverageStatus,
    ResearchGapStatus,
    ResearchPriorityLevel,
    ResearchSynthesisStatus,
)
from research.exceptions import ResearchError
from research.models import (
    ResearchAgenda,
    ResearchConflict,
    ResearchCoverage,
    ResearchGap,
    ResearchInsight,
    ResearchObservation,
    ResearchPriority,
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
    "ResearchSynthesisContext",
    "ResearchSynthesisResult",
    "ResearchSynthesizer",
]


@dataclass(frozen=True, slots=True)
class ResearchSynthesisContext:
    """Inputs for qualitative research synthesis."""

    profile: ResearchProfile
    report: ResearchReport | None = None
    decision_refs: tuple[DecisionReference, ...] | None = None
    evidence_refs: tuple[EvidenceReference, ...] | None = None
    comparison_refs: tuple[ComparisonReference, ...] | None = None
    portfolio_ref: PortfolioReference | None = None
    monitoring_ref: MonitoringReference | None = None
    risk_refs: tuple[RiskReference, ...] | None = None
    integrated_risk_refs: tuple[IntegratedRiskReference, ...] | None = None
    as_of: str | None = None

    def __post_init__(self) -> None:
        if self.profile is None:
            msg = "invalid ResearchProfile: profile is required"
            raise ResearchError(msg)
        if self.decision_refs is not None:
            object.__setattr__(self, "decision_refs", tuple(self.decision_refs))
        if self.evidence_refs is not None:
            object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        if self.comparison_refs is not None:
            object.__setattr__(self, "comparison_refs", tuple(self.comparison_refs))
        if self.risk_refs is not None:
            object.__setattr__(self, "risk_refs", tuple(self.risk_refs))
        if self.integrated_risk_refs is not None:
            object.__setattr__(
                self, "integrated_risk_refs", tuple(self.integrated_risk_refs)
            )
        as_of = None if self.as_of is None else self.as_of.strip() or None
        object.__setattr__(self, "as_of", as_of)


@dataclass(frozen=True, slots=True)
class ResearchSynthesisResult:
    """Synthesis output — qualitative research artifacts only."""

    research_id: str
    status: ResearchSynthesisStatus
    profile: ResearchProfile
    report: ResearchReport
    observations: tuple[ResearchObservation, ...]
    insights: tuple[ResearchInsight, ...]
    conflicts: tuple[ResearchConflict, ...]
    gaps: tuple[ResearchGap, ...]
    agenda: ResearchAgenda
    summary: ResearchSummary
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "observations", tuple(self.observations))
        object.__setattr__(self, "insights", tuple(self.insights))
        object.__setattr__(self, "conflicts", tuple(self.conflicts))
        object.__setattr__(self, "gaps", tuple(self.gaps))
        object.__setattr__(self, "warnings", tuple(self.warnings))


class ResearchSynthesizer:
    """Canonical qualitative synthesis layer for Research Intelligence.

    Structural / citation-based synthesis only — never upstream re-analysis.
    """

    def validate_inputs(self, context: ResearchSynthesisContext) -> None:
        """Reject invalid synthesis inputs."""
        profile = context.profile
        if profile is None or profile.identity is None:
            msg = "invalid ResearchProfile"
            raise ResearchError(msg)
        if not profile.identity.research_id:
            msg = "invalid ResearchProfile: empty research_id"
            raise ResearchError(msg)

        evidence = (
            context.evidence_refs
            if context.evidence_refs is not None
            else profile.evidence_refs
        )
        if not evidence:
            msg = "missing EvidenceReference: synthesis requires evidence citations"
            raise ResearchError(msg)

        portfolio = (
            context.portfolio_ref
            if context.portfolio_ref is not None
            else profile.portfolio_ref
        )
        monitoring = (
            context.monitoring_ref
            if context.monitoring_ref is not None
            else profile.monitoring_ref
        )
        if monitoring is not None and portfolio is not None:
            if monitoring.portfolio_id != portfolio.portfolio_id:
                msg = (
                    "foreign ownership: monitoring portfolio_id "
                    f"{monitoring.portfolio_id!r} does not match "
                    f"{portfolio.portfolio_id!r}"
                )
                raise ResearchError(msg)

        if context.report is not None:
            if context.report.research_id != profile.identity.research_id:
                msg = (
                    "foreign ownership: report research_id "
                    f"{context.report.research_id!r} does not match "
                    f"{profile.identity.research_id!r}"
                )
                raise ResearchError(msg)

    def synthesize(
        self, context: ResearchSynthesisContext | ResearchProfile
    ) -> ResearchSynthesisResult:
        """Synthesize qualitative research artifacts from assembled citations."""
        ctx = (
            ResearchSynthesisContext(profile=context)
            if isinstance(context, ResearchProfile)
            else context
        )
        self.validate_inputs(ctx)
        profile = ctx.profile
        research_id = profile.identity.research_id

        decision_refs = (
            ctx.decision_refs
            if ctx.decision_refs is not None
            else profile.decision_refs
        )
        evidence_refs = (
            ctx.evidence_refs
            if ctx.evidence_refs is not None
            else profile.evidence_refs
        )
        comparison_refs = (
            ctx.comparison_refs
            if ctx.comparison_refs is not None
            else profile.comparison_refs
        )
        portfolio_ref = (
            ctx.portfolio_ref
            if ctx.portfolio_ref is not None
            else profile.portfolio_ref
        )
        monitoring_ref = (
            ctx.monitoring_ref
            if ctx.monitoring_ref is not None
            else profile.monitoring_ref
        )
        risk_refs = (
            ctx.risk_refs if ctx.risk_refs is not None else profile.risk_refs
        )
        integrated_risk_refs = (
            ctx.integrated_risk_refs
            if ctx.integrated_risk_refs is not None
            else profile.integrated_risk_refs
        )

        coverage = self._synthesize_coverage(
            decision_refs=decision_refs,
            evidence_refs=evidence_refs,
            comparison_refs=comparison_refs,
            portfolio_ref=portfolio_ref,
            monitoring_ref=monitoring_ref,
            risk_refs=risk_refs,
            integrated_risk_refs=integrated_risk_refs,
        )
        observations = self._build_observations(
            research_id=research_id,
            evidence_refs=evidence_refs,
            coverage=coverage,
        )
        gaps = self._build_gaps(research_id=research_id, coverage=coverage)
        conflicts = self._build_conflicts(
            research_id=research_id,
            decision_refs=decision_refs,
            evidence_refs=evidence_refs,
            comparison_refs=comparison_refs,
            portfolio_ref=portfolio_ref,
            monitoring_ref=monitoring_ref,
            risk_refs=risk_refs,
            integrated_risk_refs=integrated_risk_refs,
        )
        insights = self._build_insights(
            research_id=research_id,
            observations=observations,
            evidence_refs=evidence_refs,
            decision_refs=decision_refs,
            comparison_refs=comparison_refs,
            risk_refs=risk_refs,
            gaps=gaps,
            conflicts=conflicts,
        )
        priorities = self._build_priorities(
            research_id=research_id,
            gaps=gaps,
            conflicts=conflicts,
            insights=insights,
            observations=observations,
        )
        agenda = ResearchAgenda(
            agenda_id=f"{research_id}.agenda",
            priorities=priorities,
            notes=(
                "Investigative agenda only — no portfolio or trading actions.",
            ),
        )
        summary = ResearchSummary(
            observation_count=len(observations),
            insight_count=len(insights),
            conflict_count=len(conflicts),
            gap_count=len(gaps),
            agenda_item_count=len(priorities),
            coverage_notes=tuple(
                f"{c.dimension}: {c.status.value}" for c in coverage
            ),
            limitation_notes=(
                "Qualitative synthesis only — no valuation, risk calculation, "
                "or recommendations.",
            ),
        )

        as_of = (
            ctx.as_of
            or (ctx.report.as_of if ctx.report is not None else None)
            or profile.identity.created_at
            or "synthesized"
        )

        updated_profile = ResearchProfile(
            identity=profile.identity,
            portfolio_ref=portfolio_ref,
            monitoring_ref=monitoring_ref,
            decision_refs=decision_refs,
            evidence_refs=evidence_refs,
            comparison_refs=comparison_refs,
            risk_refs=risk_refs,
            integrated_risk_refs=integrated_risk_refs,
            observations=observations,
            insights=insights,
            conflicts=conflicts,
            gaps=gaps,
            agenda=agenda,
            coverage=coverage,
            summary=summary,
            notes=profile.notes
            + ("Synthesized structurally from citations — F1.2.",),
        )
        report = ResearchReport(
            research_id=research_id,
            summary=summary,
            as_of=as_of,
            observations=observations,
            insights=insights,
            conflicts=conflicts,
            gaps=gaps,
            agenda=agenda,
            coverage=coverage,
            decision_refs=decision_refs,
            evidence_refs=evidence_refs,
            comparison_refs=comparison_refs,
            portfolio_ref=portfolio_ref,
            monitoring_ref=monitoring_ref,
            risk_refs=risk_refs,
            integrated_risk_refs=integrated_risk_refs,
            limitations=(
                "ResearchReport snapshot after synthesis — immutable; "
                "later events require a new report.",
            ),
        )

        status, warnings = self._status_and_warnings(
            insights=insights,
            gaps=gaps,
            conflicts=conflicts,
            priorities=priorities,
            coverage=coverage,
        )
        return ResearchSynthesisResult(
            research_id=research_id,
            status=status,
            profile=updated_profile,
            report=report,
            observations=observations,
            insights=insights,
            conflicts=conflicts,
            gaps=gaps,
            agenda=agenda,
            summary=summary,
            warnings=warnings,
        )

    def synthesize_many(
        self, contexts: tuple[ResearchSynthesisContext | ResearchProfile, ...]
    ) -> tuple[ResearchSynthesisResult, ...]:
        return tuple(self.synthesize(ctx) for ctx in contexts)

    def _synthesize_coverage(
        self,
        *,
        decision_refs: tuple[DecisionReference, ...],
        evidence_refs: tuple[EvidenceReference, ...],
        comparison_refs: tuple[ComparisonReference, ...],
        portfolio_ref: PortfolioReference | None,
        monitoring_ref: MonitoringReference | None,
        risk_refs: tuple[RiskReference, ...],
        integrated_risk_refs: tuple[IntegratedRiskReference, ...],
    ) -> tuple[ResearchCoverage, ...]:
        def row(dimension: str, present: bool) -> ResearchCoverage:
            if present:
                return ResearchCoverage(
                    dimension=dimension,
                    status=ResearchCoverageStatus.PARTIAL,
                    label=(
                        f"{dimension.replace('_', ' ').capitalize()} "
                        "citations appear attached."
                    ),
                )
            return ResearchCoverage(
                dimension=dimension,
                status=ResearchCoverageStatus.INSUFFICIENT,
                label=(
                    f"{dimension.replace('_', ' ').capitalize()} "
                    "citations appear absent."
                ),
            )

        return (
            row("decision", bool(decision_refs)),
            row("evidence", bool(evidence_refs)),
            row("comparison", bool(comparison_refs)),
            row("portfolio", portfolio_ref is not None),
            row("monitoring", monitoring_ref is not None),
            row("risk", bool(risk_refs) or bool(integrated_risk_refs)),
        )

    def _build_observations(
        self,
        *,
        research_id: str,
        evidence_refs: tuple[EvidenceReference, ...],
        coverage: tuple[ResearchCoverage, ...],
    ) -> tuple[ResearchObservation, ...]:
        observations: list[ResearchObservation] = []
        observations.append(
            ResearchObservation(
                observation_id=f"{research_id}.obs.evidence",
                code="evidence_citations_present",
                text="Evidence citations appear attached for synthesis.",
                evidence_refs=evidence_refs,
            )
        )
        for cov in coverage:
            if cov.status is ResearchCoverageStatus.INSUFFICIENT:
                observations.append(
                    ResearchObservation(
                        observation_id=f"{research_id}.obs.gap_{cov.dimension}",
                        code=f"{cov.dimension}_citations_absent",
                        text=(
                            f"{cov.dimension.replace('_', ' ').capitalize()} "
                            "coverage appears insufficient and needs investigation."
                        ),
                        evidence_refs=evidence_refs,
                    )
                )
            elif cov.dimension != "evidence":
                observations.append(
                    ResearchObservation(
                        observation_id=f"{research_id}.obs.cov_{cov.dimension}",
                        code=f"{cov.dimension}_citations_present",
                        text=(
                            f"{cov.dimension.replace('_', ' ').capitalize()} "
                            "citations appear present and require validation."
                        ),
                        evidence_refs=evidence_refs,
                    )
                )
        return tuple(observations)

    def _build_gaps(
        self, *, research_id: str, coverage: tuple[ResearchCoverage, ...]
    ) -> tuple[ResearchGap, ...]:
        gaps: list[ResearchGap] = []
        for cov in coverage:
            if cov.status is ResearchCoverageStatus.INSUFFICIENT:
                gaps.append(
                    ResearchGap(
                        gap_id=f"{research_id}.gap.{cov.dimension}",
                        dimension=cov.dimension,
                        status=ResearchGapStatus.OPEN,
                        description=(
                            f"{cov.dimension.replace('_', ' ').capitalize()} "
                            "knowledge appears incomplete and needs investigation."
                        ),
                        missing_refs=(f"{cov.dimension}:absent",),
                    )
                )
        return tuple(gaps)

    def _build_conflicts(
        self,
        *,
        research_id: str,
        decision_refs: tuple[DecisionReference, ...],
        evidence_refs: tuple[EvidenceReference, ...],
        comparison_refs: tuple[ComparisonReference, ...],
        portfolio_ref: PortfolioReference | None,
        monitoring_ref: MonitoringReference | None,
        risk_refs: tuple[RiskReference, ...],
        integrated_risk_refs: tuple[IntegratedRiskReference, ...],
    ) -> tuple[ResearchConflict, ...]:
        conflicts: list[ResearchConflict] = []
        if decision_refs and not comparison_refs:
            conflicts.append(
                ResearchConflict(
                    conflict_id=f"{research_id}.conflict.decision_vs_comparison",
                    summary=(
                        "Decision citations appear present while comparison "
                        "citations appear absent."
                    ),
                    severity=ResearchConflictSeverity.MODERATE,
                    left_citations=tuple(
                        f"decision:{r.instrument_symbol}:{r.digest}"
                        for r in decision_refs
                    ),
                    right_citations=("comparison:absent",),
                    notes=("Descriptive conflict only — not resolved by Research.",),
                )
            )
        if portfolio_ref is not None and monitoring_ref is None:
            conflicts.append(
                ResearchConflict(
                    conflict_id=f"{research_id}.conflict.portfolio_vs_monitoring",
                    summary=(
                        "Portfolio citation appears present while monitoring "
                        "citation appears absent."
                    ),
                    severity=ResearchConflictSeverity.LOW,
                    left_citations=(f"portfolio:{portfolio_ref.portfolio_id}",),
                    right_citations=("monitoring:absent",),
                )
            )
        if risk_refs and not integrated_risk_refs:
            conflicts.append(
                ResearchConflict(
                    conflict_id=f"{research_id}.conflict.risk_vs_integrated",
                    summary=(
                        "Risk citations appear present while integrated risk "
                        "citation appears absent."
                    ),
                    severity=ResearchConflictSeverity.LOW,
                    left_citations=tuple(f"risk:{r.risk_id}" for r in risk_refs),
                    right_citations=("integrated_risk:absent",),
                )
            )
        if evidence_refs and not decision_refs:
            conflicts.append(
                ResearchConflict(
                    conflict_id=f"{research_id}.conflict.evidence_vs_decision",
                    summary=(
                        "Evidence citations appear present while decision "
                        "citations appear absent."
                    ),
                    severity=ResearchConflictSeverity.MODERATE,
                    left_citations=tuple(
                        f"evidence:{r.bundle_id}" for r in evidence_refs
                    ),
                    right_citations=("decision:absent",),
                )
            )
        return tuple(conflicts)

    def _build_insights(
        self,
        *,
        research_id: str,
        observations: tuple[ResearchObservation, ...],
        evidence_refs: tuple[EvidenceReference, ...],
        decision_refs: tuple[DecisionReference, ...],
        comparison_refs: tuple[ComparisonReference, ...],
        risk_refs: tuple[RiskReference, ...],
        gaps: tuple[ResearchGap, ...],
        conflicts: tuple[ResearchConflict, ...],
    ) -> tuple[ResearchInsight, ...]:
        insights: list[ResearchInsight] = []
        evidence_obs = next(
            o for o in observations if o.code == "evidence_citations_present"
        )
        insights.append(
            ResearchInsight(
                insight_id=f"{research_id}.insight.evidence_basis",
                text=(
                    "Evidence supports further investigation of knowledge "
                    "coverage across cited subsystems."
                ),
                observation_ids=(evidence_obs.observation_id,),
                evidence_refs=evidence_refs,
                decision_refs=decision_refs,
                comparison_refs=comparison_refs,
                risk_refs=risk_refs,
            )
        )
        if gaps:
            gap_obs_ids = tuple(
                o.observation_id
                for o in observations
                if o.code.endswith("_citations_absent")
            )
            if gap_obs_ids:
                insights.append(
                    ResearchInsight(
                        insight_id=f"{research_id}.insight.coverage_gaps",
                        text=(
                            "Evidence indicates coverage gaps that need "
                            "investigation before research can be considered complete."
                        ),
                        observation_ids=gap_obs_ids,
                        evidence_refs=evidence_refs,
                        decision_refs=decision_refs,
                        comparison_refs=comparison_refs,
                        risk_refs=risk_refs,
                    )
                )
        if conflicts:
            insights.append(
                ResearchInsight(
                    insight_id=f"{research_id}.insight.structural_conflicts",
                    text=(
                        "Evidence indicates structural citation conflicts that "
                        "require validation by analysts."
                    ),
                    observation_ids=(evidence_obs.observation_id,),
                    evidence_refs=evidence_refs,
                    decision_refs=decision_refs,
                    comparison_refs=comparison_refs,
                    risk_refs=risk_refs,
                )
            )
        return tuple(insights)

    def _build_priorities(
        self,
        *,
        research_id: str,
        gaps: tuple[ResearchGap, ...],
        conflicts: tuple[ResearchConflict, ...],
        insights: tuple[ResearchInsight, ...],
        observations: tuple[ResearchObservation, ...],
    ) -> tuple[ResearchPriority, ...]:
        priorities: list[ResearchPriority] = []
        for gap in gaps:
            level = (
                ResearchPriorityLevel.HIGH
                if gap.dimension in {"evidence", "risk", "decision"}
                else ResearchPriorityLevel.MEDIUM
            )
            if gap.dimension == "evidence":
                level = ResearchPriorityLevel.CRITICAL
            priorities.append(
                ResearchPriority(
                    priority_id=f"{research_id}.priority.gap.{gap.dimension}",
                    level=level,
                    text=(
                        f"Needs investigation of {gap.dimension.replace('_', ' ')} "
                        "knowledge gap."
                    ),
                    gap_ids=(gap.gap_id,),
                    insight_ids=tuple(i.insight_id for i in insights[:1]),
                )
            )
        for conflict in conflicts:
            priorities.append(
                ResearchPriority(
                    priority_id=f"{research_id}.priority.conflict.{conflict.conflict_id.split('.')[-1]}",
                    level=ResearchPriorityLevel.MEDIUM
                    if conflict.severity is ResearchConflictSeverity.LOW
                    else ResearchPriorityLevel.HIGH,
                    text=(
                        "Needs investigation to reconcile a descriptive "
                        "citation conflict."
                    ),
                    conflict_ids=(conflict.conflict_id,),
                    observation_ids=(observations[0].observation_id,),
                )
            )
        if not priorities and insights:
            priorities.append(
                ResearchPriority(
                    priority_id=f"{research_id}.priority.validate_coverage",
                    level=ResearchPriorityLevel.LOW,
                    text=(
                        "Needs investigation to validate cited coverage even "
                        "where citations appear present."
                    ),
                    insight_ids=(insights[0].insight_id,),
                    observation_ids=(observations[0].observation_id,),
                )
            )
        return tuple(priorities)

    def _status_and_warnings(
        self,
        *,
        insights: tuple[ResearchInsight, ...],
        gaps: tuple[ResearchGap, ...],
        conflicts: tuple[ResearchConflict, ...],
        priorities: tuple[ResearchPriority, ...],
        coverage: tuple[ResearchCoverage, ...],
    ) -> tuple[ResearchSynthesisStatus, tuple[str, ...]]:
        warnings: list[str] = []
        if not insights and not gaps and not conflicts:
            return ResearchSynthesisStatus.EMPTY, (
                "No synthesis artifacts produced.",
            )

        insufficient = tuple(
            c.dimension
            for c in coverage
            if c.status is ResearchCoverageStatus.INSUFFICIENT
        )
        if insufficient:
            warnings.append(
                "Coverage remains insufficient for: " + ", ".join(insufficient)
            )

        if insights and priorities and not insufficient:
            status = ResearchSynthesisStatus.COMPLETE
        elif insights or gaps or conflicts:
            status = ResearchSynthesisStatus.PARTIAL
        else:
            status = ResearchSynthesisStatus.EMPTY

        warnings.append(
            "Synthesizer is citation-structural only — no Evidence reinterpretation."
        )
        return status, tuple(warnings)
