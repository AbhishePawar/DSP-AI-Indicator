"""Risk Analyzer — qualitative interpretation only (E1.2).

Consumes RiskProfile (+ optional Portfolio / Monitoring citations).
Emits observations, categorical descriptors, coverage, assessment, report.
Never computes quantitative risk, probability, returns, or recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass

from portfolio import Portfolio

from risk.enums import (
    RiskAnalysisStatus,
    RiskCoverageKind,
    RiskCoverageStatus,
    RiskLevel,
)
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
from risk.refs import MonitoringReference

__all__ = [
    "RiskAnalysisContext",
    "RiskAnalysisResult",
    "RiskAnalyzer",
]

# Descriptive holding-count / weight heuristics — labels only, not risk metrics.
_HIGH_CONCENTRATION_WEIGHT = 0.40
_MODERATE_CONCENTRATION_WEIGHT = 0.25
_HIGH_CASH = 0.20
_MODERATE_CASH = 0.05


@dataclass(frozen=True, slots=True)
class RiskAnalysisContext:
    """Inputs for qualitative risk analysis."""

    profile: RiskProfile
    portfolio: Portfolio | None = None
    monitoring_ref: MonitoringReference | None = None
    as_of: str | None = None
    base_report: RiskReport | None = None

    def __post_init__(self) -> None:
        if self.profile is None:
            msg = "invalid RiskProfile: profile is required"
            raise RiskError(msg)
        as_of = None if self.as_of is None else self.as_of.strip() or None
        object.__setattr__(self, "as_of", as_of)


@dataclass(frozen=True, slots=True)
class RiskAnalysisResult:
    """Qualitative analysis output — descriptive only."""

    risk_id: str
    status: RiskAnalysisStatus
    assessment: RiskAssessment
    observations: tuple[RiskObservation, ...]
    descriptors: tuple[RiskDescriptor, ...]
    coverage: tuple[RiskCoverage, ...]
    summary: RiskSummary
    report: RiskReport
    profile: RiskProfile
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "observations", tuple(self.observations))
        object.__setattr__(self, "descriptors", tuple(self.descriptors))
        object.__setattr__(self, "coverage", tuple(self.coverage))
        object.__setattr__(self, "warnings", tuple(self.warnings))


class RiskAnalyzer:
    """Canonical qualitative interpretation layer for Risk Intelligence.

    Descriptive posture only — never quantitative risk or trading advice.
    """

    def validate_inputs(self, context: RiskAnalysisContext) -> None:
        """Reject invalid analysis inputs."""
        profile = context.profile
        if profile is None or profile.identity is None:
            msg = "invalid RiskProfile"
            raise RiskError(msg)
        if not profile.identity.risk_id:
            msg = "invalid RiskProfile: empty risk_id"
            raise RiskError(msg)
        if profile.portfolio_ref is None:
            msg = "broken references: portfolio_ref is required"
            raise RiskError(msg)

        if context.portfolio is not None:
            if context.portfolio.portfolio_id != profile.portfolio_ref.portfolio_id:
                msg = (
                    "foreign ownership: portfolio "
                    f"{context.portfolio.portfolio_id!r} does not match "
                    f"{profile.portfolio_ref.portfolio_id!r}"
                )
                raise RiskError(msg)

        monitoring = context.monitoring_ref or profile.monitoring_ref
        if monitoring is not None:
            if monitoring.portfolio_id != profile.portfolio_ref.portfolio_id:
                msg = (
                    "foreign ownership: monitoring portfolio_id "
                    f"{monitoring.portfolio_id!r} does not match "
                    f"{profile.portfolio_ref.portfolio_id!r}"
                )
                raise RiskError(msg)

        if context.base_report is not None:
            if context.base_report.risk_id != profile.identity.risk_id:
                msg = (
                    "foreign ownership: base_report risk_id "
                    f"{context.base_report.risk_id!r}"
                )
                raise RiskError(msg)
            if context.base_report.portfolio_id != profile.portfolio_ref.portfolio_id:
                msg = (
                    "foreign ownership: base_report portfolio_id "
                    f"{context.base_report.portfolio_id!r}"
                )
                raise RiskError(msg)

    def analyze(
        self, context: RiskAnalysisContext | RiskProfile
    ) -> RiskAnalysisResult:
        """Run qualitative risk analysis — descriptive only."""
        ctx = (
            RiskAnalysisContext(profile=context)
            if isinstance(context, RiskProfile)
            else context
        )
        self.validate_inputs(ctx)
        profile = ctx.profile

        holding_count = self._holding_count(ctx)
        cash_weight = self._cash_weight(ctx)

        descriptors = self._build_descriptors(ctx, holding_count, cash_weight)
        coverage = self._build_coverage(profile)
        observations = self._build_observations(
            ctx, descriptors, coverage, holding_count
        )
        self._reject_duplicates(observations, descriptors)

        summary = RiskSummary(
            observation_count=len(observations),
            descriptor_count=len(descriptors),
            coverage_notes=tuple(c.label for c in coverage),
            posture_notes=tuple(
                f"{d.dimension}: {d.label}" for d in descriptors
            ),
            limitation_notes=(
                "Qualitative risk analysis only — no quantitative risk metrics.",
                "No trading, optimization, or recommendations.",
            ),
        )

        as_of = self._as_of(ctx)
        assessment_id = (
            f"dsp.risk.assessment.{profile.identity.risk_id}."
            f"{as_of.lower().replace(':', '').replace('-', '').replace('t', '')}"
        )
        for existing in profile.assessments:
            if existing.assessment_id == assessment_id:
                msg = f"duplicate assessments: {assessment_id!r}"
                raise RiskError(msg)

        assessment = RiskAssessment(
            assessment_id=assessment_id,
            risk_id=profile.identity.risk_id,
            portfolio_id=profile.portfolio_ref.portfolio_id,
            as_of=as_of,
            observations=observations,
            descriptors=descriptors,
            coverage=coverage,
            summary=summary,
            notes=("E1.2 qualitative assessment — descriptive only.",),
        )

        updated_profile = RiskProfile(
            identity=profile.identity,
            portfolio_ref=profile.portfolio_ref,
            monitoring_ref=ctx.monitoring_ref or profile.monitoring_ref,
            decision_pack_refs=profile.decision_pack_refs,
            evidence_bundle_refs=profile.evidence_bundle_refs,
            comparison_report_refs=profile.comparison_report_refs,
            constraints=profile.constraints,
            assessments=profile.assessments + (assessment,),
            notes=profile.notes,
        )

        report = self._build_report(ctx, assessment, summary)
        status = self._status(holding_count, coverage, cash_weight)
        warnings = self._warnings(ctx, coverage, cash_weight)

        return RiskAnalysisResult(
            risk_id=profile.identity.risk_id,
            status=status,
            assessment=assessment,
            observations=observations,
            descriptors=descriptors,
            coverage=coverage,
            summary=summary,
            report=report,
            profile=updated_profile,
            warnings=warnings,
        )

    def analyze_many(
        self, contexts: tuple[RiskAnalysisContext | RiskProfile, ...]
    ) -> tuple[RiskAnalysisResult, ...]:
        return tuple(self.analyze(ctx) for ctx in contexts)

    def _as_of(self, context: RiskAnalysisContext) -> str:
        if context.as_of:
            return context.as_of
        if context.profile.identity.created_at:
            return context.profile.identity.created_at
        if context.profile.portfolio_ref.snapshot_id:
            return context.profile.portfolio_ref.snapshot_id
        return "unspecified"

    def _holding_count(self, context: RiskAnalysisContext) -> int:
        if context.portfolio is not None:
            return len(context.portfolio.holdings)
        return len(context.profile.decision_pack_refs)

    def _cash_weight(self, context: RiskAnalysisContext) -> float | None:
        if context.portfolio is None:
            return None
        if context.portfolio.cash_weight is not None:
            return context.portfolio.cash_weight
        if context.portfolio.snapshots:
            snap = context.portfolio.snapshots[-1]
            if snap.cash_weight is not None:
                return snap.cash_weight
        return None

    def _max_weight(self, context: RiskAnalysisContext) -> float | None:
        if context.portfolio is None:
            return None
        weights = [h.weight for h in context.portfolio.holdings if h.weight is not None]
        return max(weights) if weights else None

    def _build_descriptors(
        self,
        context: RiskAnalysisContext,
        holding_count: int,
        cash_weight: float | None,
    ) -> tuple[RiskDescriptor, ...]:
        max_w = self._max_weight(context)
        concentration = self._concentration_descriptor(holding_count, max_w)
        diversification = self._diversification_descriptor(holding_count)
        cash = self._cash_descriptor(cash_weight)
        liquidity = self._liquidity_descriptor(cash_weight, holding_count)
        constraint = self._constraint_descriptor(context.profile)
        return (
            concentration,
            diversification,
            cash,
            liquidity,
            constraint,
        )

    def _concentration_descriptor(
        self, holding_count: int, max_weight: float | None
    ) -> RiskDescriptor:
        if holding_count == 0:
            return RiskDescriptor(
                dimension="concentration",
                level=RiskLevel.UNKNOWN,
                label="Concentration posture unknown",
                notes=("No holdings or DecisionPack citations available.",),
            )
        if holding_count == 1 or (
            max_weight is not None and max_weight >= _HIGH_CONCENTRATION_WEIGHT
        ):
            return RiskDescriptor(
                dimension="concentration",
                level=RiskLevel.HIGH,
                label="Concentration elevated",
                notes=("Descriptive label from holding count / declared weights.",),
            )
        if holding_count <= 5 or (
            max_weight is not None and max_weight >= _MODERATE_CONCENTRATION_WEIGHT
        ):
            return RiskDescriptor(
                dimension="concentration",
                level=RiskLevel.ELEVATED,
                label="Concentration moderate to elevated",
                notes=("Descriptive label from holding count / declared weights.",),
            )
        return RiskDescriptor(
            dimension="concentration",
            level=RiskLevel.LOW,
            label="Concentration limited",
            notes=("Descriptive label from holding count / declared weights.",),
        )

    def _diversification_descriptor(self, holding_count: int) -> RiskDescriptor:
        if holding_count == 0:
            return RiskDescriptor(
                dimension="diversification",
                level=RiskLevel.UNKNOWN,
                label="Diversification posture unknown",
            )
        if holding_count == 1:
            return RiskDescriptor(
                dimension="diversification",
                level=RiskLevel.HIGH,
                label="Diversification is limited",
            )
        if holding_count <= 4:
            return RiskDescriptor(
                dimension="diversification",
                level=RiskLevel.ELEVATED,
                label="Diversification is limited",
            )
        if holding_count <= 8:
            return RiskDescriptor(
                dimension="diversification",
                level=RiskLevel.MODERATE,
                label="Diversification is moderate",
            )
        return RiskDescriptor(
            dimension="diversification",
            level=RiskLevel.LOW,
            label="Diversification is broad",
        )

    def _cash_descriptor(self, cash_weight: float | None) -> RiskDescriptor:
        if cash_weight is None:
            return RiskDescriptor(
                dimension="cash",
                level=RiskLevel.UNKNOWN,
                label="Cash posture unknown",
                notes=("Cash weight not supplied on optional Portfolio.",),
            )
        if cash_weight < _MODERATE_CASH:
            return RiskDescriptor(
                dimension="cash",
                level=RiskLevel.LOW,
                label="Cash posture fully invested",
            )
        if cash_weight < _HIGH_CASH:
            return RiskDescriptor(
                dimension="cash",
                level=RiskLevel.MODERATE,
                label="Cash posture moderate reserve",
            )
        return RiskDescriptor(
            dimension="cash",
            level=RiskLevel.ELEVATED,
            label="Cash posture elevated reserve",
        )

    def _liquidity_descriptor(
        self, cash_weight: float | None, holding_count: int
    ) -> RiskDescriptor:
        if cash_weight is None and holding_count == 0:
            return RiskDescriptor(
                dimension="liquidity",
                level=RiskLevel.UNKNOWN,
                label="Liquidity posture unknown",
            )
        if cash_weight is not None and cash_weight >= _HIGH_CASH:
            return RiskDescriptor(
                dimension="liquidity",
                level=RiskLevel.LOW,
                label="Liquidity posture is acceptable",
                notes=("Qualitative cash-reserve proxy only — not market liquidity.",),
            )
        if holding_count <= 1:
            return RiskDescriptor(
                dimension="liquidity",
                level=RiskLevel.ELEVATED,
                label="Liquidity posture may be constrained",
                notes=("Qualitative holding-count proxy only — not market liquidity.",),
            )
        return RiskDescriptor(
            dimension="liquidity",
            level=RiskLevel.MODERATE,
            label="Liquidity posture is acceptable",
            notes=("Qualitative proxy only — not market liquidity.",),
        )

    def _constraint_descriptor(self, profile: RiskProfile) -> RiskDescriptor:
        if not profile.constraints:
            return RiskDescriptor(
                dimension="constraint",
                level=RiskLevel.UNKNOWN,
                label="Constraint posture unknown",
                notes=("No risk constraints declared.",),
            )
        # Descriptive only — do not evaluate mathematically.
        levels = {c.posture for c in profile.constraints}
        if RiskLevel.HIGH in levels or RiskLevel.ELEVATED in levels:
            level = RiskLevel.ELEVATED
            label = "Constraint posture requires attention"
        else:
            level = RiskLevel.LOW
            label = "Constraint posture is acceptable"
        return RiskDescriptor(
            dimension="constraint",
            level=level,
            label=label,
            notes=("Constraints are not evaluated mathematically in E1.2.",),
        )

    def _build_coverage(self, profile: RiskProfile) -> tuple[RiskCoverage, ...]:
        n_decision = len(profile.decision_pack_refs)
        n_evidence = len(profile.evidence_bundle_refs)
        n_comparison = len(profile.comparison_report_refs)

        if n_decision == 0:
            decision = RiskCoverage(
                kind=RiskCoverageKind.DECISION,
                status=RiskCoverageStatus.ABSENT,
                label="Decision coverage absent",
            )
        else:
            decision = RiskCoverage(
                kind=RiskCoverageKind.DECISION,
                status=RiskCoverageStatus.COMPLETE,
                label="Decision coverage is complete",
            )

        if n_decision == 0 and n_evidence == 0:
            evidence = RiskCoverage(
                kind=RiskCoverageKind.EVIDENCE,
                status=RiskCoverageStatus.ABSENT,
                label="Evidence coverage is incomplete",
            )
        elif n_evidence == 0:
            evidence = RiskCoverage(
                kind=RiskCoverageKind.EVIDENCE,
                status=RiskCoverageStatus.ABSENT,
                label="Evidence coverage is incomplete",
            )
        elif n_evidence < n_decision:
            evidence = RiskCoverage(
                kind=RiskCoverageKind.EVIDENCE,
                status=RiskCoverageStatus.PARTIAL,
                label="Evidence coverage is incomplete",
            )
        else:
            evidence = RiskCoverage(
                kind=RiskCoverageKind.EVIDENCE,
                status=RiskCoverageStatus.COMPLETE,
                label="Evidence coverage is complete",
            )

        if n_comparison == 0:
            comparison = RiskCoverage(
                kind=RiskCoverageKind.COMPARISON,
                status=RiskCoverageStatus.ABSENT,
                label="Comparison coverage absent",
            )
        else:
            comparison = RiskCoverage(
                kind=RiskCoverageKind.COMPARISON,
                status=RiskCoverageStatus.COMPLETE,
                label="Comparison coverage present",
            )

        return (decision, evidence, comparison)

    def _build_observations(
        self,
        context: RiskAnalysisContext,
        descriptors: tuple[RiskDescriptor, ...],
        coverage: tuple[RiskCoverage, ...],
        holding_count: int,
    ) -> tuple[RiskObservation, ...]:
        by_dim = {d.dimension: d for d in descriptors}
        observations: list[RiskObservation] = []

        conc = by_dim["concentration"]
        if conc.level in {RiskLevel.HIGH, RiskLevel.ELEVATED}:
            text = "Portfolio appears concentrated."
        elif conc.level is RiskLevel.LOW:
            text = "Portfolio concentration appears limited."
        else:
            text = "Concentration posture is unknown."
        observations.append(
            RiskObservation(
                code="concentration_posture",
                text=text,
                subjects=tuple(
                    r.instrument_symbol
                    for r in context.profile.decision_pack_refs
                ),
            )
        )

        div = by_dim["diversification"]
        if div.level in {RiskLevel.HIGH, RiskLevel.ELEVATED}:
            text = "Diversification is limited."
        elif div.level is RiskLevel.MODERATE:
            text = "Diversification is moderate."
        elif div.level is RiskLevel.LOW:
            text = "Diversification appears broad."
        else:
            text = "Diversification posture is unknown."
        observations.append(
            RiskObservation(code="diversification_posture", text=text)
        )

        cash = by_dim["cash"]
        observations.append(
            RiskObservation(
                code="cash_posture",
                text=f"Cash posture: {cash.label}.",
            )
        )

        for cov in coverage:
            if cov.kind is RiskCoverageKind.EVIDENCE:
                observations.append(
                    RiskObservation(
                        code="evidence_coverage_posture",
                        text=(
                            "Evidence coverage is incomplete."
                            if cov.status
                            in {
                                RiskCoverageStatus.ABSENT,
                                RiskCoverageStatus.PARTIAL,
                            }
                            else "Evidence coverage is complete."
                        ),
                    )
                )
            elif cov.kind is RiskCoverageKind.DECISION:
                observations.append(
                    RiskObservation(
                        code="decision_coverage_posture",
                        text=(
                            "Decision coverage is complete."
                            if cov.status is RiskCoverageStatus.COMPLETE
                            else "Decision coverage is incomplete."
                        ),
                    )
                )

        constraint = by_dim["constraint"]
        observations.append(
            RiskObservation(
                code="constraint_posture",
                text=f"{constraint.label}.",
            )
        )

        liquidity = by_dim["liquidity"]
        observations.append(
            RiskObservation(
                code="liquidity_posture",
                text=f"{liquidity.label}.",
            )
        )

        if holding_count == 0:
            observations.append(
                RiskObservation(
                    code="empty_holding_surface",
                    text="No holdings or DecisionPack citations were available.",
                )
            )

        return tuple(observations)

    def _build_report(
        self,
        context: RiskAnalysisContext,
        assessment: RiskAssessment,
        summary: RiskSummary,
    ) -> RiskReport:
        profile = context.profile
        base = context.base_report
        limitations = list(summary.limitation_notes)
        if base is not None:
            limitations = list(base.limitations) + limitations
        return RiskReport(
            risk_id=profile.identity.risk_id,
            portfolio_id=profile.portfolio_ref.portfolio_id,
            summary=summary,
            observations=assessment.observations,
            descriptors=assessment.descriptors,
            coverage=assessment.coverage,
            assessment_id=assessment.assessment_id,
            decision_pack_refs=profile.decision_pack_refs,
            evidence_bundle_refs=profile.evidence_bundle_refs,
            comparison_report_refs=profile.comparison_report_refs,
            limitations=tuple(dict.fromkeys(limitations)),
        )

    def _status(
        self,
        holding_count: int,
        coverage: tuple[RiskCoverage, ...],
        cash_weight: float | None,
    ) -> RiskAnalysisStatus:
        if holding_count == 0:
            return RiskAnalysisStatus.EMPTY
        evidence = next(
            c for c in coverage if c.kind is RiskCoverageKind.EVIDENCE
        )
        if (
            evidence.status
            in {RiskCoverageStatus.ABSENT, RiskCoverageStatus.PARTIAL}
            or cash_weight is None
        ):
            return RiskAnalysisStatus.PARTIAL
        return RiskAnalysisStatus.COMPLETE

    def _warnings(
        self,
        context: RiskAnalysisContext,
        coverage: tuple[RiskCoverage, ...],
        cash_weight: float | None,
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        if context.portfolio is None:
            warnings.append(
                "Optional Portfolio not supplied — structure postures use "
                "DecisionPack citation counts only."
            )
        if cash_weight is None:
            warnings.append("Cash posture unknown — cash_weight not supplied.")
        for cov in coverage:
            if cov.status in {
                RiskCoverageStatus.ABSENT,
                RiskCoverageStatus.PARTIAL,
            }:
                warnings.append(cov.label)
        if context.profile.constraints:
            warnings.append(
                "Declared risk constraints were not evaluated mathematically."
            )
        return tuple(dict.fromkeys(warnings))

    def _reject_duplicates(
        self,
        observations: tuple[RiskObservation, ...],
        descriptors: tuple[RiskDescriptor, ...],
    ) -> None:
        seen_obs: set[str] = set()
        for obs in observations:
            if obs.code in seen_obs:
                msg = f"duplicate observations: code {obs.code!r}"
                raise RiskError(msg)
            seen_obs.add(obs.code)
        seen_dim: set[str] = set()
        for desc in descriptors:
            if desc.dimension in seen_dim:
                msg = f"duplicate descriptors: dimension {desc.dimension!r}"
                raise RiskError(msg)
            seen_dim.add(desc.dimension)
