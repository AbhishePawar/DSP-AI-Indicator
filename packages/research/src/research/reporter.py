"""Research Reporter — presentation / assembly only (F1.3).

Assembles existing synthesized Research artifacts into a canonical ResearchReport.
Never synthesizes insights, detects conflicts, creates agenda, or recommends actions.
"""

from __future__ import annotations

from dataclasses import dataclass

from research.enums import ResearchReportingStatus
from research.exceptions import ResearchError
from research.models import (
    ResearchAgenda,
    ResearchConflict,
    ResearchCoverage,
    ResearchGap,
    ResearchInsight,
    ResearchObservation,
    ResearchProfile,
    ResearchReport,
    ResearchSummary,
)

__all__ = [
    "ResearchReporter",
    "ResearchReportingContext",
    "ResearchReportingResult",
]


@dataclass(frozen=True, slots=True)
class ResearchReportingContext:
    """Inputs for canonical ResearchReport presentation."""

    profile: ResearchProfile
    summary: ResearchSummary | None = None
    observations: tuple[ResearchObservation, ...] | None = None
    insights: tuple[ResearchInsight, ...] | None = None
    conflicts: tuple[ResearchConflict, ...] | None = None
    gaps: tuple[ResearchGap, ...] | None = None
    agenda: ResearchAgenda | None = None
    coverage: tuple[ResearchCoverage, ...] | None = None
    base_report: ResearchReport | None = None
    as_of: str | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.profile is None:
            msg = "invalid ResearchProfile: profile is required"
            raise ResearchError(msg)
        if self.observations is not None:
            object.__setattr__(self, "observations", tuple(self.observations))
        if self.insights is not None:
            object.__setattr__(self, "insights", tuple(self.insights))
        if self.conflicts is not None:
            object.__setattr__(self, "conflicts", tuple(self.conflicts))
        if self.gaps is not None:
            object.__setattr__(self, "gaps", tuple(self.gaps))
        if self.coverage is not None:
            object.__setattr__(self, "coverage", tuple(self.coverage))
        as_of = None if self.as_of is None else self.as_of.strip() or None
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(
            self, "limitations", tuple(n.strip() for n in self.limitations if n.strip())
        )


@dataclass(frozen=True, slots=True)
class ResearchReportingResult:
    """Reporting output — canonical ResearchReport only."""

    report: ResearchReport
    status: ResearchReportingStatus
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", tuple(self.warnings))


class ResearchReporter:
    """Canonical presentation layer for Research Intelligence.

    Organizes existing artifacts — never invents synthesis.
    """

    def validate_inputs(self, context: ResearchReportingContext) -> None:
        """Reject invalid reporting inputs."""
        profile = context.profile
        if profile is None or profile.identity is None:
            msg = "invalid ResearchProfile"
            raise ResearchError(msg)
        if not profile.identity.research_id:
            msg = "invalid ResearchProfile: missing identity"
            raise ResearchError(msg)

        if not profile.evidence_refs and (
            context.base_report is None or not context.base_report.evidence_refs
        ):
            msg = "missing citations: EvidenceReference required"
            raise ResearchError(msg)

        if context.base_report is not None:
            if context.base_report.research_id != profile.identity.research_id:
                msg = (
                    "foreign ownership: report research_id "
                    f"{context.base_report.research_id!r} does not match "
                    f"{profile.identity.research_id!r}"
                )
                raise ResearchError(msg)

        if context.insights is not None:
            self._reject_duplicate_insight_ids(context.insights)
        if context.conflicts is not None:
            self._reject_duplicate_conflict_ids(context.conflicts)
        if context.gaps is not None:
            self._reject_duplicate_gap_ids(context.gaps)
        if context.coverage is not None:
            self._reject_duplicate_coverage_dimensions(context.coverage)
        if context.agenda is not None:
            self._reject_duplicate_priority_ids(context.agenda)

        for ref in profile.decision_refs:
            if not ref.digest or len(ref.digest) < 8:
                msg = "broken references: DecisionReference digest invalid"
                raise ResearchError(msg)
        for ref in profile.evidence_refs:
            if not ref.bundle_id or not ref.digest:
                msg = "broken references: EvidenceReference invalid"
                raise ResearchError(msg)
        for ref in profile.comparison_refs:
            if not ref.digest or len(ref.digest) < 8:
                msg = "broken references: ComparisonReference digest invalid"
                raise ResearchError(msg)

        if (
            profile.monitoring_ref is not None
            and profile.portfolio_ref is not None
            and profile.monitoring_ref.portfolio_id
            != profile.portfolio_ref.portfolio_id
        ):
            msg = (
                "foreign ownership: monitoring portfolio_id "
                f"{profile.monitoring_ref.portfolio_id!r} does not match "
                f"{profile.portfolio_ref.portfolio_id!r}"
            )
            raise ResearchError(msg)

    def report(
        self, context: ResearchReportingContext | ResearchProfile
    ) -> ResearchReportingResult:
        """Assemble a canonical ResearchReport from existing artifacts."""
        ctx = (
            ResearchReportingContext(profile=context)
            if isinstance(context, ResearchProfile)
            else context
        )
        self.validate_inputs(ctx)
        profile = ctx.profile
        base = ctx.base_report

        summary = self._resolve_summary(ctx, base)
        if summary is None:
            msg = "missing summary: ResearchSummary is required"
            raise ResearchError(msg)

        coverage = self._resolve_coverage(ctx, base)
        if not coverage:
            msg = "missing coverage: ResearchCoverage is required"
            raise ResearchError(msg)

        observations = (
            ctx.observations
            if ctx.observations is not None
            else (
                base.observations
                if base is not None and base.observations
                else profile.observations
            )
        )
        insights = (
            ctx.insights
            if ctx.insights is not None
            else (
                base.insights
                if base is not None and base.insights
                else profile.insights
            )
        )
        conflicts = (
            ctx.conflicts
            if ctx.conflicts is not None
            else (
                base.conflicts
                if base is not None and base.conflicts
                else profile.conflicts
            )
        )
        gaps = (
            ctx.gaps
            if ctx.gaps is not None
            else (base.gaps if base is not None and base.gaps else profile.gaps)
        )
        agenda = (
            ctx.agenda
            if ctx.agenda is not None
            else (
                base.agenda
                if base is not None and base.agenda is not None
                else profile.agenda
            )
        )

        self._reject_duplicate_insight_ids(insights)
        self._reject_duplicate_conflict_ids(conflicts)
        self._reject_duplicate_gap_ids(gaps)
        self._reject_duplicate_coverage_dimensions(coverage)
        if agenda is not None:
            self._reject_duplicate_priority_ids(agenda)

        self._validate_insight_provenance(insights, observations)

        as_of = (
            ctx.as_of
            or (base.as_of if base is not None else None)
            or profile.identity.created_at
            or "reported"
        )

        limitations = list(ctx.limitations)
        limitations.extend(summary.limitation_notes)
        if base is not None:
            limitations.extend(base.limitations)
        limitations.append(
            "ResearchReport presentation only — no synthesis performed by reporter."
        )

        report = ResearchReport(
            research_id=profile.identity.research_id,
            summary=summary,
            as_of=as_of,
            observations=observations,
            insights=insights,
            conflicts=conflicts,
            gaps=gaps,
            agenda=agenda,
            coverage=coverage,
            decision_refs=profile.decision_refs,
            evidence_refs=profile.evidence_refs,
            comparison_refs=profile.comparison_refs,
            portfolio_ref=profile.portfolio_ref,
            monitoring_ref=profile.monitoring_ref,
            risk_refs=profile.risk_refs,
            integrated_risk_refs=profile.integrated_risk_refs,
            limitations=tuple(dict.fromkeys(limitations)),
        )

        status = self._status(insights, conflicts, gaps, coverage, summary, agenda)
        warnings: list[str] = []
        if status is ResearchReportingStatus.PARTIAL:
            warnings.append("Report sections are incomplete.")
        if status is ResearchReportingStatus.EMPTY:
            warnings.append("Report contains no insights, conflicts, or gaps.")

        return ResearchReportingResult(
            report=report,
            status=status,
            warnings=tuple(warnings),
        )

    def report_many(
        self, contexts: tuple[ResearchReportingContext | ResearchProfile, ...]
    ) -> tuple[ResearchReportingResult, ...]:
        seen: set[str] = set()
        results: list[ResearchReportingResult] = []
        for ctx in contexts:
            profile = ctx if isinstance(ctx, ResearchProfile) else ctx.profile
            rid = profile.identity.research_id
            if rid in seen:
                msg = f"duplicate report identities: research_id {rid!r}"
                raise ResearchError(msg)
            seen.add(rid)
            results.append(self.report(ctx))
        return tuple(results)

    def _resolve_summary(
        self,
        context: ResearchReportingContext,
        base: ResearchReport | None,
    ) -> ResearchSummary | None:
        if context.summary is not None:
            return context.summary
        if context.profile.summary is not None:
            return context.profile.summary
        if base is not None:
            return base.summary
        return None

    def _resolve_coverage(
        self,
        context: ResearchReportingContext,
        base: ResearchReport | None,
    ) -> tuple[ResearchCoverage, ...]:
        if context.coverage is not None:
            return context.coverage
        if context.profile.coverage:
            return context.profile.coverage
        if base is not None:
            return base.coverage
        return ()

    def _status(
        self,
        insights: tuple[ResearchInsight, ...],
        conflicts: tuple[ResearchConflict, ...],
        gaps: tuple[ResearchGap, ...],
        coverage: tuple[ResearchCoverage, ...],
        summary: ResearchSummary,
        agenda: ResearchAgenda | None,
    ) -> ResearchReportingStatus:
        if not insights and not conflicts and not gaps:
            return ResearchReportingStatus.EMPTY
        has_agenda = agenda is not None and bool(agenda.priorities)
        if (
            insights
            and coverage
            and summary.insight_count > 0
            and has_agenda
        ):
            return ResearchReportingStatus.COMPLETE
        return ResearchReportingStatus.PARTIAL

    def _validate_insight_provenance(
        self,
        insights: tuple[ResearchInsight, ...],
        observations: tuple[ResearchObservation, ...],
    ) -> None:
        obs_ids = {o.observation_id for o in observations}
        for insight in insights:
            if not insight.evidence_refs:
                msg = (
                    f"missing provenance: insight {insight.insight_id!r} "
                    "requires EvidenceReference"
                )
                raise ResearchError(msg)
            if not insight.observation_ids:
                msg = (
                    f"missing provenance: insight {insight.insight_id!r} "
                    "requires observation_ids"
                )
                raise ResearchError(msg)
            for oid in insight.observation_ids:
                if oid not in obs_ids:
                    msg = (
                        f"broken references: insight {insight.insight_id!r} "
                        f"references missing observation {oid!r}"
                    )
                    raise ResearchError(msg)

    def _reject_duplicate_insight_ids(
        self, insights: tuple[ResearchInsight, ...]
    ) -> None:
        seen: set[str] = set()
        for insight in insights:
            if insight.insight_id in seen:
                msg = f"duplicate report sections: insight {insight.insight_id!r}"
                raise ResearchError(msg)
            seen.add(insight.insight_id)

    def _reject_duplicate_conflict_ids(
        self, conflicts: tuple[ResearchConflict, ...]
    ) -> None:
        seen: set[str] = set()
        for conflict in conflicts:
            if conflict.conflict_id in seen:
                msg = (
                    f"duplicate report sections: conflict {conflict.conflict_id!r}"
                )
                raise ResearchError(msg)
            seen.add(conflict.conflict_id)

    def _reject_duplicate_gap_ids(self, gaps: tuple[ResearchGap, ...]) -> None:
        seen: set[str] = set()
        for gap in gaps:
            if gap.gap_id in seen:
                msg = f"duplicate report sections: gap {gap.gap_id!r}"
                raise ResearchError(msg)
            seen.add(gap.gap_id)

    def _reject_duplicate_coverage_dimensions(
        self, coverage: tuple[ResearchCoverage, ...]
    ) -> None:
        seen: set[str] = set()
        for cov in coverage:
            if cov.dimension in seen:
                msg = (
                    f"duplicate report sections: coverage dimension "
                    f"{cov.dimension!r}"
                )
                raise ResearchError(msg)
            seen.add(cov.dimension)

    def _reject_duplicate_priority_ids(self, agenda: ResearchAgenda) -> None:
        seen: set[str] = set()
        for priority in agenda.priorities:
            if priority.priority_id in seen:
                msg = (
                    f"duplicate report sections: priority "
                    f"{priority.priority_id!r}"
                )
                raise ResearchError(msg)
            seen.add(priority.priority_id)
