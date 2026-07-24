"""Risk Integration — coordination / aggregation only (E1.4).

Aggregates existing qualitative Risk artifacts into IntegratedRiskContext.
Never analyzes, monitors, creates observations, assigns RiskLevel, or computes risk.
"""

from __future__ import annotations

from dataclasses import dataclass

from risk.enums import RiskIntegrationStatus
from risk.exceptions import RiskError
from risk.models import (
    RiskAssessment,
    RiskCoverage,
    RiskProfile,
    RiskReport,
    RiskSummary,
)

__all__ = [
    "IntegratedRiskContext",
    "RiskIntegrationContext",
    "RiskIntegrationResult",
    "RiskIntegrator",
]


@dataclass(frozen=True, slots=True)
class RiskIntegrationContext:
    """Inputs for qualitative Risk artifact coordination."""

    profile: RiskProfile
    assessment: RiskAssessment | None = None
    summary: RiskSummary | None = None
    coverage: tuple[RiskCoverage, ...] | None = None
    report: RiskReport | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.profile is None:
            msg = "invalid RiskProfile: profile is required"
            raise RiskError(msg)
        if self.coverage is not None:
            object.__setattr__(self, "coverage", tuple(self.coverage))
        object.__setattr__(
            self, "notes", tuple(n.strip() for n in self.notes if n.strip())
        )


@dataclass(frozen=True, slots=True)
class IntegratedRiskContext:
    """Coherent bundle of existing qualitative Risk artifacts.

    Prepared for downstream reporting / monitoring consumers — never analysis.
    """

    profile: RiskProfile
    assessment: RiskAssessment | None = None
    summary: RiskSummary | None = None
    coverage: tuple[RiskCoverage, ...] = ()
    report: RiskReport | None = None
    reporting_inputs_ready: bool = False
    monitoring_inputs_ready: bool = False
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "coverage", tuple(self.coverage))
        object.__setattr__(self, "notes", tuple(self.notes))


@dataclass(frozen=True, slots=True)
class RiskIntegrationResult:
    """Integration output — coordinated artifacts only."""

    context: IntegratedRiskContext
    status: RiskIntegrationStatus
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", tuple(self.warnings))


class RiskIntegrator:
    """Canonical coordination layer for qualitative Risk artifacts.

    Combines existing artifacts — never invents analysis or monitoring.
    """

    def validate_inputs(self, context: RiskIntegrationContext) -> None:
        """Reject invalid or inconsistent integration inputs."""
        profile = context.profile
        if profile is None or profile.identity is None:
            msg = "invalid RiskProfile"
            raise RiskError(msg)
        if not profile.identity.risk_id or not profile.portfolio_ref:
            msg = "invalid RiskProfile: missing identity or portfolio_ref"
            raise RiskError(msg)

        self._validate_profile_references(profile)

        assessment = self._resolve_assessment(context, require=False)
        if assessment is not None:
            self._validate_assessment_ownership(profile, assessment)
            if context.assessment is not None:
                self._reject_duplicate_assessment(profile, context.assessment)

        report = context.report
        if report is not None:
            self._validate_report_ownership(profile, report)
            if assessment is not None and report.assessment_id is not None:
                if report.assessment_id != assessment.assessment_id:
                    msg = (
                        "broken references: report assessment_id "
                        f"{report.assessment_id!r} does not match "
                        f"{assessment.assessment_id!r}"
                    )
                    raise RiskError(msg)

        coverage = (
            context.coverage
            if context.coverage is not None
            else (assessment.coverage if assessment is not None else ())
        )
        self._reject_duplicate_coverage(coverage)

        if (
            context.summary is not None
            and assessment is not None
            and assessment.summary is not None
            and context.summary is not assessment.summary
            and (
                context.summary.observation_count
                != assessment.summary.observation_count
                or context.summary.descriptor_count
                != assessment.summary.descriptor_count
            )
        ):
            msg = "broken references: summary counts do not match assessment"
            raise RiskError(msg)

    def integrate(
        self, context: RiskIntegrationContext | RiskProfile
    ) -> RiskIntegrationResult:
        """Aggregate existing Risk artifacts into IntegratedRiskContext."""
        ctx = (
            RiskIntegrationContext(profile=context)
            if isinstance(context, RiskProfile)
            else context
        )
        self.validate_inputs(ctx)
        profile = ctx.profile

        assessment = self._resolve_assessment(ctx, require=False)
        summary = self._resolve_summary(ctx, assessment)
        coverage = self._resolve_coverage(ctx, assessment)
        report = ctx.report

        notes = list(ctx.notes)
        notes.append(
            "IntegratedRiskContext coordination only — no analysis or monitoring."
        )

        reporting_ready = assessment is not None and summary is not None
        # Prepare monitoring inputs: identity + portfolio citation only.
        # Does not interpret Monitoring state or run monitoring.
        monitoring_ready = bool(profile.portfolio_ref.portfolio_id)
        if profile.monitoring_ref is not None:
            notes.append(
                "Monitoring citation present — ready for downstream monitoring consumers."
            )
        else:
            notes.append(
                "No Monitoring citation — portfolio reference prepared for downstream use."
            )

        integrated = IntegratedRiskContext(
            profile=profile,
            assessment=assessment,
            summary=summary,
            coverage=coverage,
            report=report,
            reporting_inputs_ready=reporting_ready,
            monitoring_inputs_ready=monitoring_ready,
            notes=tuple(dict.fromkeys(notes)),
        )

        status = self._status(assessment, summary, coverage, report)
        warnings: list[str] = []
        if status is RiskIntegrationStatus.PARTIAL:
            warnings.append("Integration is incomplete — some artifacts absent.")
        if status is RiskIntegrationStatus.EMPTY:
            warnings.append("No assessment, summary, coverage, or report to integrate.")
        if not reporting_ready:
            warnings.append("Reporting inputs not ready — assessment or summary missing.")

        return RiskIntegrationResult(
            context=integrated,
            status=status,
            warnings=tuple(warnings),
        )

    def integrate_many(
        self, contexts: tuple[RiskIntegrationContext | RiskProfile, ...]
    ) -> tuple[RiskIntegrationResult, ...]:
        return tuple(self.integrate(ctx) for ctx in contexts)

    def _resolve_assessment(
        self, context: RiskIntegrationContext, *, require: bool
    ) -> RiskAssessment | None:
        if context.assessment is not None:
            return context.assessment
        if context.profile.assessments:
            return context.profile.assessments[-1]
        if require:
            msg = "missing required artifacts: RiskAssessment"
            raise RiskError(msg)
        return None

    def _resolve_summary(
        self,
        context: RiskIntegrationContext,
        assessment: RiskAssessment | None,
    ) -> RiskSummary | None:
        if context.summary is not None:
            return context.summary
        if assessment is not None:
            return assessment.summary
        if context.report is not None:
            return context.report.summary
        return None

    def _resolve_coverage(
        self,
        context: RiskIntegrationContext,
        assessment: RiskAssessment | None,
    ) -> tuple[RiskCoverage, ...]:
        if context.coverage is not None:
            return context.coverage
        if assessment is not None:
            return assessment.coverage
        if context.report is not None:
            return context.report.coverage
        return ()

    def _status(
        self,
        assessment: RiskAssessment | None,
        summary: RiskSummary | None,
        coverage: tuple[RiskCoverage, ...],
        report: RiskReport | None,
    ) -> RiskIntegrationStatus:
        has_any = (
            assessment is not None
            or summary is not None
            or bool(coverage)
            or report is not None
        )
        if not has_any:
            return RiskIntegrationStatus.EMPTY
        if (
            assessment is not None
            and summary is not None
            and bool(coverage)
            and report is not None
        ):
            return RiskIntegrationStatus.COMPLETE
        return RiskIntegrationStatus.PARTIAL

    def _validate_profile_references(self, profile: RiskProfile) -> None:
        for ref in profile.decision_pack_refs:
            if not ref.digest or len(ref.digest) < 8:
                msg = "broken references: DecisionPack digest invalid"
                raise RiskError(msg)
        for ref in profile.evidence_bundle_refs:
            if not ref.bundle_id or not ref.digest:
                msg = "broken references: EvidenceBundle citation invalid"
                raise RiskError(msg)
        for ref in profile.comparison_report_refs:
            if not ref.digest or len(ref.digest) < 8:
                msg = "broken references: ComparisonReport digest invalid"
                raise RiskError(msg)
        if profile.monitoring_ref is not None:
            if (
                profile.monitoring_ref.portfolio_id
                != profile.portfolio_ref.portfolio_id
            ):
                msg = (
                    "foreign ownership: monitoring portfolio_id "
                    f"{profile.monitoring_ref.portfolio_id!r} does not match "
                    f"{profile.portfolio_ref.portfolio_id!r}"
                )
                raise RiskError(msg)

    def _validate_assessment_ownership(
        self, profile: RiskProfile, assessment: RiskAssessment
    ) -> None:
        if assessment.risk_id != profile.identity.risk_id:
            msg = (
                f"foreign ownership: assessment risk_id "
                f"{assessment.risk_id!r} does not match "
                f"{profile.identity.risk_id!r}"
            )
            raise RiskError(msg)
        if assessment.portfolio_id != profile.portfolio_ref.portfolio_id:
            msg = (
                f"foreign ownership: assessment portfolio_id "
                f"{assessment.portfolio_id!r} does not match "
                f"{profile.portfolio_ref.portfolio_id!r}"
            )
            raise RiskError(msg)

    def _validate_report_ownership(
        self, profile: RiskProfile, report: RiskReport
    ) -> None:
        if report.risk_id != profile.identity.risk_id:
            msg = (
                f"foreign ownership: report risk_id "
                f"{report.risk_id!r} does not match "
                f"{profile.identity.risk_id!r}"
            )
            raise RiskError(msg)
        if report.portfolio_id != profile.portfolio_ref.portfolio_id:
            msg = (
                f"foreign ownership: report portfolio_id "
                f"{report.portfolio_id!r} does not match "
                f"{profile.portfolio_ref.portfolio_id!r}"
            )
            raise RiskError(msg)

    def _reject_duplicate_assessment(
        self, profile: RiskProfile, assessment: RiskAssessment
    ) -> None:
        for existing in profile.assessments:
            if existing.assessment_id == assessment.assessment_id:
                msg = (
                    "duplicate artifacts: assessment "
                    f"{assessment.assessment_id!r} already on profile"
                )
                raise RiskError(msg)

    def _reject_duplicate_coverage(
        self, coverage: tuple[RiskCoverage, ...]
    ) -> None:
        seen: set[str] = set()
        for cov in coverage:
            key = cov.kind.value
            if key in seen:
                msg = f"duplicate artifacts: coverage kind {key!r}"
                raise RiskError(msg)
            seen.add(key)
