"""Research Synthesizer tests (F1.2)."""

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
    ResearchPriorityLevel,
    ResearchSynthesizer,
    ResearchSynthesisContext,
    ResearchSynthesisStatus,
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


def _assembled(*, full: bool = False, evidence_only: bool = False):
    if evidence_only:
        ctx = ResearchAssemblyContext(
            identity=_identity(),
            evidence_refs=(_evidence(),),
        )
    elif full:
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
            decision_refs=(
                DecisionReference(
                    instrument_symbol="AAA", digest="abcdef0123456789"
                ),
            ),
            portfolio_ref=PortfolioReference(portfolio_id="dsp.portfolio.demo"),
            as_of="2026-07-21",
        )
    return ResearchAssembler().assemble(ctx)


class TestSynthesis:
    def test_basic_synthesis(self) -> None:
        assembled = _assembled()
        result = ResearchSynthesizer().synthesize(assembled.profile)
        assert result.insights
        assert result.observations
        assert result.agenda.priorities
        assert result.summary.insight_count == len(result.insights)
        assert result.report.insights
        for insight in result.insights:
            assert insight.evidence_refs
            assert insight.observation_ids

    def test_gaps_and_conflicts(self) -> None:
        result = ResearchSynthesizer().synthesize(_assembled(evidence_only=True).profile)
        assert result.gaps
        assert result.conflicts
        assert result.status is ResearchSynthesisStatus.PARTIAL
        assert all(g.status.value == "open" for g in result.gaps)

    def test_complete_when_citations_full(self) -> None:
        result = ResearchSynthesizer().synthesize(_assembled(full=True).profile)
        assert result.status is ResearchSynthesisStatus.COMPLETE
        assert result.insights
        assert result.agenda.priorities
        assert not result.gaps

    def test_priorities_qualitative(self) -> None:
        result = ResearchSynthesizer().synthesize(
            _assembled(evidence_only=True).profile
        )
        levels = {p.level for p in result.agenda.priorities}
        assert levels <= set(ResearchPriorityLevel)
        assert ResearchPriorityLevel.CRITICAL in levels or ResearchPriorityLevel.HIGH in levels

    def test_immutability(self) -> None:
        result = ResearchSynthesizer().synthesize(_assembled().profile)
        with pytest.raises(AttributeError):
            result.insights = ()  # type: ignore[misc]
        with pytest.raises(AttributeError):
            result.report.gaps = ()  # type: ignore[misc]


class TestValidation:
    def test_missing_evidence(self) -> None:
        assembled = _assembled()
        with pytest.raises(ResearchError, match="EvidenceReference"):
            ResearchSynthesizer().synthesize(
                ResearchSynthesisContext(
                    profile=assembled.profile,
                    evidence_refs=(),
                )
            )

    def test_foreign_report(self) -> None:
        assembled = _assembled()
        other = ResearchAssembler().assemble(
            ResearchAssemblyContext(
                identity=ResearchIdentity(
                    research_id="dsp.research.other",
                    research_name="Other",
                ),
                evidence_refs=(_evidence(),),
            )
        )
        with pytest.raises(ResearchError, match="foreign ownership"):
            ResearchSynthesizer().synthesize(
                ResearchSynthesisContext(
                    profile=assembled.profile,
                    report=other.report,
                )
            )

    def test_claim_language_in_artifacts(self) -> None:
        result = ResearchSynthesizer().synthesize(_assembled().profile)
        blob = " ".join(i.text.lower() for i in result.insights)
        for term in ("buy", "sell", "hold", "optimize", "guaranteed"):
            assert term not in blob.split()


class TestArchitectureAndCompatibility:
    def test_architecture_boundaries(self) -> None:
        path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "research"
            / "synthesizer.py"
        )
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        assert "portfolio" not in imported
        assert "risk" not in imported
        assert "industry" not in imported
        assert "ResearchReporter" not in source
        assert "BUY" not in source
        assert "SELL" not in source
        assert "sharpe" not in source.lower()
        assert "re-analyz" in source.lower() or "reinterpretation" in source.lower()

    def test_backward_compatibility(self) -> None:
        import research as rs

        assert rs.ResearchAssembler is not None
        assert rs.ResearchSynthesizer is not None
        assert rs.ResearchSynthesisStatus.COMPLETE.value == "complete"
        assert rs.ResearchReporter is not None
        assert rs.__version__ == "0.4.0"

        assembled = _assembled(full=True)
        synthesized = ResearchSynthesizer().synthesize(
            ResearchSynthesisContext(
                profile=assembled.profile,
                report=assembled.report,
            )
        )
        assert synthesized.report.research_id == assembled.profile.research_id

    def test_platform_exports(self) -> None:
        import dsp_platform as platform

        assert platform.ResearchSynthesizer is ResearchSynthesizer
        assert platform.ResearchSynthesisStatus.PARTIAL.value == "partial"
