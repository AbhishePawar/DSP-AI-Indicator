"""Research domain model tests (F1.0)."""

from __future__ import annotations

import pytest
from core.exceptions import ValidationError

from research import (
    ComparisonReference,
    DecisionReference,
    EvidenceReference,
    IntegratedRiskReference,
    MonitoringReference,
    PortfolioReference,
    ResearchAgenda,
    ResearchConflict,
    ResearchConflictSeverity,
    ResearchCoverage,
    ResearchCoverageStatus,
    ResearchError,
    ResearchGap,
    ResearchGapStatus,
    ResearchIdentity,
    ResearchInsight,
    ResearchObservation,
    ResearchPriority,
    ResearchPriorityLevel,
    ResearchProfile,
    ResearchReport,
    ResearchSummary,
    RiskReference,
)


def _identity() -> ResearchIdentity:
    return ResearchIdentity(
        research_id="dsp.research.demo",
        research_name="Demo Research",
        created_at="2026-07-21T00:00:00Z",
    )


def _evidence() -> EvidenceReference:
    return EvidenceReference(
        bundle_id="dsp.evidence_bundle.aaa",
        digest="abcdef0123456789deadbeef",
        instrument_key="AAA",
    )


def _observation() -> ResearchObservation:
    return ResearchObservation(
        observation_id="dsp.research.obs.1",
        code="evidence_partial",
        text="Evidence appears incomplete for cited holdings.",
        evidence_refs=(_evidence(),),
    )


def _insight() -> ResearchInsight:
    return ResearchInsight(
        insight_id="dsp.research.insight.1",
        text="Evidence supports further investigation of coverage gaps.",
        observation_ids=("dsp.research.obs.1",),
        evidence_refs=(_evidence(),),
    )


class TestIdentityAndConstruction:
    def test_identity(self) -> None:
        identity = _identity()
        assert identity.research_id == "dsp.research.demo"
        assert identity.research_name == "Demo Research"

    def test_empty_identity_name_rejected(self) -> None:
        with pytest.raises(ValidationError, match="research_name"):
            ResearchIdentity(research_id="dsp.research.x", research_name="  ")

    def test_profile_aggregate(self) -> None:
        obs = _observation()
        insight = _insight()
        gap = ResearchGap(
            gap_id="dsp.research.gap.evidence",
            dimension="evidence",
            status=ResearchGapStatus.OPEN,
            description="Evidence coverage needs investigation.",
            missing_refs=("dsp.evidence_bundle.bbb",),
        )
        conflict = ResearchConflict(
            conflict_id="dsp.research.conflict.1",
            summary="Evidence contradicts comparison coverage notes.",
            severity=ResearchConflictSeverity.MODERATE,
            left_citations=("evidence:abcdef0123456789deadbeef",),
            right_citations=("comparison:abcdef0123456789",),
        )
        priority = ResearchPriority(
            priority_id="dsp.research.priority.1",
            level=ResearchPriorityLevel.HIGH,
            text="Needs investigation of evidence coverage gap.",
            gap_ids=(gap.gap_id,),
        )
        profile = ResearchProfile(
            identity=_identity(),
            portfolio_ref=PortfolioReference(portfolio_id="dsp.portfolio.demo"),
            monitoring_ref=MonitoringReference(portfolio_id="dsp.portfolio.demo"),
            decision_refs=(
                DecisionReference(
                    instrument_symbol="AAA",
                    digest="abcdef0123456789",
                ),
            ),
            evidence_refs=(_evidence(),),
            comparison_refs=(ComparisonReference(digest="abcdef0123456789"),),
            risk_refs=(RiskReference(risk_id="dsp.risk.demo"),),
            integrated_risk_refs=(
                IntegratedRiskReference(risk_id="dsp.risk.demo"),
            ),
            observations=(obs,),
            insights=(insight,),
            conflicts=(conflict,),
            gaps=(gap,),
            agenda=ResearchAgenda(
                agenda_id="dsp.research.agenda.1",
                priorities=(priority,),
            ),
            coverage=(
                ResearchCoverage(
                    dimension="evidence",
                    status=ResearchCoverageStatus.PARTIAL,
                    label="Evidence coverage appears partial.",
                ),
            ),
            summary=ResearchSummary(
                observation_count=1,
                insight_count=1,
                conflict_count=1,
                gap_count=1,
                agenda_item_count=1,
                limitation_notes=("Synthesis only — no recommendations.",),
            ),
        )
        assert profile.research_id == "dsp.research.demo"
        assert len(profile.insights) == 1
        assert profile.agenda is not None

    def test_report_immutable_snapshot(self) -> None:
        obs = _observation()
        report = ResearchReport(
            research_id="dsp.research.demo",
            as_of="2026-07-21",
            summary=ResearchSummary(
                observation_count=1,
                insight_count=1,
                limitation_notes=("Immutable snapshot.",),
            ),
            observations=(obs,),
            insights=(_insight(),),
            evidence_refs=(_evidence(),),
            limitations=("ResearchReport is a snapshot in time.",),
        )
        with pytest.raises(AttributeError):
            report.observations = ()  # type: ignore[misc]


class TestValidation:
    def test_duplicate_observations(self) -> None:
        obs = _observation()
        with pytest.raises(ResearchError, match="duplicate observations"):
            ResearchProfile(
                identity=_identity(),
                portfolio_ref=PortfolioReference(portfolio_id="dsp.portfolio.demo"),
                observations=(obs, obs),
            )

    def test_duplicate_insights(self) -> None:
        insight = _insight()
        with pytest.raises(ResearchError, match="duplicate insights"):
            ResearchProfile(
                identity=_identity(),
                evidence_refs=(_evidence(),),
                observations=(_observation(),),
                insights=(insight, insight),
            )

    def test_duplicate_conflicts(self) -> None:
        conflict = ResearchConflict(
            conflict_id="dsp.research.conflict.1",
            summary="Evidence indicates a coverage conflict.",
            severity=ResearchConflictSeverity.LOW,
            left_citations=("a",),
            right_citations=("b",),
        )
        with pytest.raises(ResearchError, match="duplicate conflicts"):
            ResearchProfile(
                identity=_identity(),
                portfolio_ref=PortfolioReference(portfolio_id="dsp.portfolio.demo"),
                conflicts=(conflict, conflict),
            )

    def test_duplicate_gaps(self) -> None:
        gap = ResearchGap(
            gap_id="dsp.research.gap.1",
            dimension="decision",
            status=ResearchGapStatus.OPEN,
            description="Decision coverage requires validation.",
        )
        with pytest.raises(ResearchError, match="duplicate gaps"):
            ResearchProfile(
                identity=_identity(),
                portfolio_ref=PortfolioReference(portfolio_id="dsp.portfolio.demo"),
                gaps=(gap, gap),
            )

    def test_duplicate_priorities(self) -> None:
        gap = ResearchGap(
            gap_id="dsp.research.gap.1",
            dimension="evidence",
            status=ResearchGapStatus.OPEN,
            description="Evidence coverage needs investigation.",
        )
        priority = ResearchPriority(
            priority_id="dsp.research.priority.1",
            level=ResearchPriorityLevel.MEDIUM,
            text="Needs investigation of evidence gap.",
            gap_ids=(gap.gap_id,),
        )
        with pytest.raises(ResearchError, match="duplicate priorities"):
            ResearchAgenda(
                agenda_id="dsp.research.agenda.1",
                priorities=(priority, priority),
            )

    def test_insight_requires_evidence(self) -> None:
        with pytest.raises(ResearchError, match="EvidenceReference"):
            ResearchInsight(
                insight_id="dsp.research.insight.x",
                text="Evidence appears incomplete.",
                observation_ids=("dsp.research.obs.1",),
                evidence_refs=(),
            )

    def test_insight_broken_observation_ref(self) -> None:
        with pytest.raises(ResearchError, match="missing observation"):
            ResearchProfile(
                identity=_identity(),
                evidence_refs=(_evidence(),),
                observations=(_observation(),),
                insights=(
                    ResearchInsight(
                        insight_id="dsp.research.insight.1",
                        text="Evidence supports further investigation.",
                        observation_ids=("dsp.research.obs.missing",),
                        evidence_refs=(_evidence(),),
                    ),
                ),
            )

    def test_foreign_monitoring_ownership(self) -> None:
        with pytest.raises(ResearchError, match="foreign ownership"):
            ResearchProfile(
                identity=_identity(),
                portfolio_ref=PortfolioReference(portfolio_id="dsp.portfolio.demo"),
                monitoring_ref=MonitoringReference(portfolio_id="dsp.portfolio.other"),
            )

    def test_missing_citations(self) -> None:
        with pytest.raises(ResearchError, match="missing citations"):
            ResearchProfile(identity=_identity())

    def test_claim_language_rejected(self) -> None:
        with pytest.raises(ValidationError, match="forbidden term"):
            ResearchObservation(
                observation_id="dsp.research.obs.x",
                code="bad",
                text="Must buy this name.",
            )

    def test_broken_decision_digest(self) -> None:
        with pytest.raises(ValidationError, match="digest invalid"):
            DecisionReference(instrument_symbol="AAA", digest="short")


class TestPlatformExport:
    def test_platform_exports(self) -> None:
        import dsp_platform as platform

        assert platform.ResearchIdentity is ResearchIdentity
        assert platform.ResearchProfile is ResearchProfile
        assert platform.ResearchPriorityLevel.HIGH.value == "high"
        assert platform.EvidenceReference is EvidenceReference
