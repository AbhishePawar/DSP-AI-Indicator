"""Risk Reporter — presentation / assembly only (E1.3).

Assembles existing qualitative Risk artifacts into a canonical RiskReport.
Never analyzes, creates observations, assigns RiskLevel, or computes risk.
"""

from __future__ import annotations

from dataclasses import dataclass

from risk.enums import RiskReportingStatus
from risk.exceptions import RiskError
from risk.models import (
    RiskAssessment,
    RiskCoverage,
    RiskDescriptor,
    RiskObservation,
    RiskProfile,
    RiskReport,
    RiskSummary,
)

__all__ = [
    "RiskReporter",
    "RiskReportingContext",
    "RiskReportingResult",
]


@dataclass(frozen=True, slots=True)
class RiskReportingContext:
    """Inputs for canonical RiskReport presentation."""

    profile: RiskProfile
    assessment: RiskAssessment | None = None
    summary: RiskSummary | None = None
    observations: tuple[RiskObservation, ...] | None = None
    descriptors: tuple[RiskDescriptor, ...] | None = None
    coverage: tuple[RiskCoverage, ...] | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.profile is None:
            msg = "invalid RiskProfile: profile is required"
            raise RiskError(msg)
        if self.observations is not None:
            object.__setattr__(self, "observations", tuple(self.observations))
        if self.descriptors is not None:
            object.__setattr__(self, "descriptors", tuple(self.descriptors))
        if self.coverage is not None:
            object.__setattr__(self, "coverage", tuple(self.coverage))
        object.__setattr__(
            self, "limitations", tuple(n.strip() for n in self.limitations if n.strip())
        )


@dataclass(frozen=True, slots=True)
class RiskReportingResult:
    """Reporting output — canonical RiskReport only."""

    report: RiskReport
    status: RiskReportingStatus
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", tuple(self.warnings))


class RiskReporter:
    """Canonical presentation layer for qualitative Risk Intelligence.

    Organizes existing artifacts — never invents analysis.
    """

    def validate_inputs(self, context: RiskReportingContext) -> None:
        """Reject invalid reporting inputs."""
        profile = context.profile
        if profile is None or profile.identity is None:
            msg = "invalid RiskProfile"
            raise RiskError(msg)
        if not profile.identity.risk_id or not profile.portfolio_ref:
            msg = "invalid RiskProfile: missing identity or portfolio_ref"
            raise RiskError(msg)

        assessment = self._resolve_assessment(context, require=False)
        if assessment is not None:
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

        # Explicit overlays must not introduce duplicate section keys.
        if context.observations is not None:
            self._reject_duplicate_observation_codes(context.observations)
        if context.descriptors is not None:
            self._reject_duplicate_descriptor_dimensions(context.descriptors)
        if context.coverage is not None:
            self._reject_duplicate_coverage_kinds(context.coverage)

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

    def report(
        self, context: RiskReportingContext | RiskProfile
    ) -> RiskReportingResult:
        """Assemble a canonical RiskReport from existing artifacts."""
        ctx = (
            RiskReportingContext(profile=context)
            if isinstance(context, RiskProfile)
            else context
        )
        self.validate_inputs(ctx)
        profile = ctx.profile

        assessment = self._resolve_assessment(ctx, require=False)
        warnings: list[str] = []

        if assessment is None:
            msg = "missing required artifacts: RiskAssessment"
            raise RiskError(msg)

        summary = ctx.summary if ctx.summary is not None else assessment.summary
        if summary is None:
            msg = "missing required artifacts: RiskSummary"
            raise RiskError(msg)

        observations = (
            ctx.observations
            if ctx.observations is not None
            else assessment.observations
        )
        descriptors = (
            ctx.descriptors
            if ctx.descriptors is not None
            else assessment.descriptors
        )
        coverage = (
            ctx.coverage if ctx.coverage is not None else assessment.coverage
        )

        # Re-validate resolved sections for duplicate keys.
        self._reject_duplicate_observation_codes(observations)
        self._reject_duplicate_descriptor_dimensions(descriptors)
        self._reject_duplicate_coverage_kinds(coverage)

        limitations = list(ctx.limitations)
        limitations.extend(summary.limitation_notes)
        limitations.append(
            "RiskReport presentation only — no analysis performed by reporter."
        )

        report = RiskReport(
            risk_id=profile.identity.risk_id,
            portfolio_id=profile.portfolio_ref.portfolio_id,
            summary=summary,
            observations=observations,
            descriptors=descriptors,
            coverage=coverage,
            assessment_id=assessment.assessment_id,
            decision_pack_refs=profile.decision_pack_refs,
            evidence_bundle_refs=profile.evidence_bundle_refs,
            comparison_report_refs=profile.comparison_report_refs,
            limitations=tuple(dict.fromkeys(limitations)),
        )

        status = self._status(observations, descriptors, coverage, summary)
        if status is RiskReportingStatus.PARTIAL:
            warnings.append("Report sections are incomplete.")
        if status is RiskReportingStatus.EMPTY:
            warnings.append("Report contains no observations or descriptors.")

        return RiskReportingResult(
            report=report,
            status=status,
            warnings=tuple(warnings),
        )

    def report_many(
        self, contexts: tuple[RiskReportingContext | RiskProfile, ...]
    ) -> tuple[RiskReportingResult, ...]:
        return tuple(self.report(ctx) for ctx in contexts)

    def _resolve_assessment(
        self, context: RiskReportingContext, *, require: bool
    ) -> RiskAssessment | None:
        if context.assessment is not None:
            return context.assessment
        if context.profile.assessments:
            return context.profile.assessments[-1]
        if require:
            msg = "missing required artifacts: RiskAssessment"
            raise RiskError(msg)
        return None

    def _status(
        self,
        observations: tuple[RiskObservation, ...],
        descriptors: tuple[RiskDescriptor, ...],
        coverage: tuple[RiskCoverage, ...],
        summary: RiskSummary,
    ) -> RiskReportingStatus:
        if not observations and not descriptors and not coverage:
            return RiskReportingStatus.EMPTY
        if (
            not observations
            or not descriptors
            or not coverage
            or summary.observation_count == 0
        ):
            return RiskReportingStatus.PARTIAL
        return RiskReportingStatus.COMPLETE

    def _reject_duplicate_observation_codes(
        self, observations: tuple[RiskObservation, ...]
    ) -> None:
        seen: set[str] = set()
        for obs in observations:
            if obs.code in seen:
                msg = f"duplicate report sections: observation code {obs.code!r}"
                raise RiskError(msg)
            seen.add(obs.code)

    def _reject_duplicate_descriptor_dimensions(
        self, descriptors: tuple[RiskDescriptor, ...]
    ) -> None:
        seen: set[str] = set()
        for desc in descriptors:
            if desc.dimension in seen:
                msg = (
                    f"duplicate report sections: descriptor dimension "
                    f"{desc.dimension!r}"
                )
                raise RiskError(msg)
            seen.add(desc.dimension)

    def _reject_duplicate_coverage_kinds(
        self, coverage: tuple[RiskCoverage, ...]
    ) -> None:
        seen: set[str] = set()
        for cov in coverage:
            key = cov.kind.value
            if key in seen:
                msg = f"duplicate report sections: coverage kind {key!r}"
                raise RiskError(msg)
            seen.add(key)
