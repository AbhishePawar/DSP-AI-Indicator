"""Research Reporter tests (F1.3)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from research import (
    ComparisonReference,
    DecisionReference,
    EvidenceReference,
    IntegratedRiskReference,
    MonitoringReference,
    PortfolioReference,
    ResearchAssembler,
    ResearchAssemblyContext,
    ResearchError,
    ResearchIdentity,
    ResearchInsight,
    ResearchReporter,
    ResearchReportingContext,
    ResearchReportingStatus,
    ResearchSummary,
    ResearchSynthesizer,
    ResearchSynthesisContext,
    RiskReference,
)


def _identity() -> ResearchIdentity:
    return ResearchIdentity(
        research_id="dsp.research.demo",
        research_name="Demo Research",
    )


def _evidence() -> EvidenceReference:
    return EvidenceReference(
        bundle_id="dsp.evidence_bundle.aaa",
        digest="abcdef0123456789deadbeef",
        instrument_key="AAA",
    )


def _synthesized(*, full: bool = True):
    if full:
        ctx = ResearchAssemblyContext(
            identity=_identity(),
            evidence_refs=(_evidence(),),
            decision_refs=(
                DecisionReference(
                    instrument_symbol="AAA", digest="abcdef0123456789"
                ),
            ),
            comparison_refs=(ComparisonReference(digest="abcdef0123456789"),),
            portfolio_ref=PortfolioReference(portfolio_id="dsp.portfolio.demo"),
            monitoring_ref=MonitoringReference(portfolio_id="dsp.portfolio.demo"),
            risk_refs=(RiskReference(risk_id="dsp.risk.demo"),),
            integrated_risk_refs=(
                IntegratedRiskReference(risk_id="dsp.risk.demo"),
            ),
            as_of="2026-07-21",
        )
    else:
        ctx = ResearchAssemblyContext(
            identity=_identity(),
            evidence_refs=(_evidence(),),
            portfolio_ref=PortfolioReference(portfolio_id="dsp.portfolio.demo"),
            as_of="2026-07-21",
        )
    assembled = ResearchAssembler().assemble(ctx)
    return ResearchSynthesizer().synthesize(
        ResearchSynthesisContext(
            profile=assembled.profile,
            report=assembled.report,
        )
    )


class TestReporting:
    def test_basic_reporting(self) -> None:
        synthesized = _synthesized()
        result = ResearchReporter().report(synthesized.profile)
        assert result.report.research_id == "dsp.research.demo"
        assert result.report.insights
        assert result.report.summary is not None
        assert result.report.coverage
        assert result.report.evidence_refs

    def test_complete_reporting(self) -> None:
        synthesized = _synthesized(full=True)
        result = ResearchReporter().report(
            ResearchReportingContext(
                profile=synthesized.profile,
                base_report=synthesized.report,
            )
        )
        assert result.status is ResearchReportingStatus.COMPLETE
        assert result.report.agenda is not None
        assert result.report.agenda.priorities

    def test_partial_reporting(self) -> None:
        synthesized = _synthesized(full=False)
        # Drop agenda via overlay empty agenda replacement by reporting without agenda
        # on a profile that has insights but we force empty agenda through context.
        from research import ResearchAgenda

        result = ResearchReporter().report(
            ResearchReportingContext(
                profile=synthesized.profile,
                agenda=ResearchAgenda(
                    agenda_id="dsp.research.demo.agenda.empty",
                    priorities=(),
                ),
            )
        )
        assert result.status is ResearchReportingStatus.PARTIAL
        assert result.warnings

    def test_immutability(self) -> None:
        result = ResearchReporter().report(_synthesized().profile)
        with pytest.raises(AttributeError):
            result.report = result.report  # type: ignore[misc]
        with pytest.raises(AttributeError):
            result.report.insights = ()  # type: ignore[misc]


class TestValidation:
    def test_missing_summary(self) -> None:
        synthesized = _synthesized()
        # Build reporting context that clears summary by using profile without summary
        # and explicit None - need profile with summary=None
        from research.models import ResearchProfile

        bare = ResearchProfile(
            identity=_identity(),
            evidence_refs=(_evidence(),),
            coverage=synthesized.profile.coverage,
            observations=synthesized.profile.observations,
            insights=synthesized.profile.insights,
            summary=None,
        )
        with pytest.raises(ResearchError, match="missing summary"):
            ResearchReporter().report(bare)

    def test_missing_coverage(self) -> None:
        synthesized = _synthesized()
        from research.models import ResearchProfile

        bare = ResearchProfile(
            identity=_identity(),
            evidence_refs=(_evidence(),),
            summary=synthesized.summary,
            observations=synthesized.observations,
            insights=(),
            coverage=(),
        )
        with pytest.raises(ResearchError, match="missing coverage"):
            ResearchReporter().report(bare)

    def test_foreign_ownership(self) -> None:
        synthesized = _synthesized()
        other = _synthesized()
        # change other report id by synthesizing with different identity
        other_assembled = ResearchAssembler().assemble(
            ResearchAssemblyContext(
                identity=ResearchIdentity(
                    research_id="dsp.research.other",
                    research_name="Other",
                ),
                evidence_refs=(_evidence(),),
            )
        )
        other_syn = ResearchSynthesizer().synthesize(other_assembled.profile)
        with pytest.raises(ResearchError, match="foreign ownership"):
            ResearchReporter().report(
                ResearchReportingContext(
                    profile=synthesized.profile,
                    base_report=other_syn.report,
                )
            )

    def test_missing_provenance(self) -> None:
        synthesized = _synthesized()
        bad_insight = ResearchInsight(
            insight_id="dsp.research.insight.orphan",
            text="Evidence supports further investigation.",
            observation_ids=("dsp.research.obs.missing",),
            evidence_refs=(_evidence(),),
        )
        with pytest.raises(ResearchError, match="broken references|missing"):
            ResearchReporter().report(
                ResearchReportingContext(
                    profile=synthesized.profile,
                    insights=(bad_insight,),
                )
            )

    def test_duplicate_report_identities(self) -> None:
        synthesized = _synthesized()
        with pytest.raises(ResearchError, match="duplicate report identities"):
            ResearchReporter().report_many(
                (synthesized.profile, synthesized.profile)
            )


class TestArchitectureAndCompatibility:
    def test_architecture_boundaries(self) -> None:
        path = (
            Path(__file__).resolve().parents[1] / "src" / "research" / "reporter.py"
        )
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        assert "research.synthesizer" not in imported
        assert "ResearchSynthesizer" not in source
        assert "synthesize(" not in source
        assert "BUY" not in source
        assert "SELL" not in source

    def test_backward_compatibility(self) -> None:
        import research as rs

        assert rs.ResearchAssembler is not None
        assert rs.ResearchSynthesizer is not None
        assert rs.ResearchReporter is not None
        assert rs.ResearchReportingStatus.COMPLETE.value == "complete"
        assert rs.__version__ == "0.4.0"

        synthesized = _synthesized(full=True)
        presented = ResearchReporter().report(
            ResearchReportingContext(
                profile=synthesized.profile,
                base_report=synthesized.report,
            )
        )
        assert presented.report.research_id == synthesized.research_id
        assert len(presented.report.insights) == len(synthesized.insights)

    def test_platform_exports(self) -> None:
        import dsp_platform as platform

        assert platform.ResearchReporter is ResearchReporter
        assert platform.ResearchReportingStatus.PARTIAL.value == "partial"
