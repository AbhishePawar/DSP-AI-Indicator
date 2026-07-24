"""Research Assembler tests (F1.1)."""

from __future__ import annotations

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
    ResearchAssemblyStatus,
    ResearchError,
    ResearchIdentity,
    RiskReference,
)


def _identity(research_id: str = "dsp.research.demo") -> ResearchIdentity:
    return ResearchIdentity(research_id=research_id, research_name="Demo Research")


def _evidence() -> EvidenceReference:
    return EvidenceReference(
        bundle_id="dsp.evidence_bundle.aaa",
        digest="abcdef0123456789deadbeef",
        instrument_key="AAA",
    )


def _ctx(
    *,
    research_id: str = "dsp.research.demo",
    full: bool = False,
    evidence_only: bool = False,
) -> ResearchAssemblyContext:
    if evidence_only:
        return ResearchAssemblyContext(
            identity=_identity(research_id),
            evidence_refs=(_evidence(),),
        )
    if full:
        return ResearchAssemblyContext(
            identity=_identity(research_id),
            evidence_refs=(_evidence(),),
            decision_refs=(
                DecisionReference(
                    instrument_symbol="AAA",
                    digest="abcdef0123456789",
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
    return ResearchAssemblyContext(
        identity=_identity(research_id),
        evidence_refs=(_evidence(),),
        portfolio_ref=PortfolioReference(portfolio_id="dsp.portfolio.demo"),
        decision_refs=(
            DecisionReference(
                instrument_symbol="AAA",
                digest="abcdef0123456789",
            ),
        ),
        as_of="2026-07-21",
    )


class TestAssembly:
    def test_basic_partial_assembly(self) -> None:
        result = ResearchAssembler().assemble(_ctx())
        assert result.status is ResearchAssemblyStatus.PARTIAL
        assert result.profile.insights == ()
        assert result.profile.conflicts == ()
        assert result.profile.gaps == ()
        assert result.profile.agenda is not None
        assert result.profile.agenda.priorities == ()
        assert result.report.summary.observation_count == 0
        assert result.report.insights == ()
        assert len(result.profile.coverage) == 6
        assert result.warnings

    def test_complete_assembly(self) -> None:
        result = ResearchAssembler().assemble(_ctx(full=True))
        assert result.status is ResearchAssemblyStatus.COMPLETE
        assert result.profile.monitoring_ref is not None
        assert result.profile.evidence_refs
        assert result.profile.risk_refs

    def test_empty_structural_shell(self) -> None:
        result = ResearchAssembler().assemble(_ctx(evidence_only=True))
        assert result.status is ResearchAssemblyStatus.EMPTY
        assert result.profile.portfolio_ref is None
        assert result.profile.decision_refs == ()

    def test_assemble_many_deterministic(self) -> None:
        assembler = ResearchAssembler()
        a = assembler.assemble_many(
            (_ctx(research_id="dsp.research.a"), _ctx(research_id="dsp.research.b"))
        )
        b = assembler.assemble_many(
            (_ctx(research_id="dsp.research.a"), _ctx(research_id="dsp.research.b"))
        )
        assert a == b

    def test_immutability(self) -> None:
        result = ResearchAssembler().assemble(_ctx())
        with pytest.raises(AttributeError):
            result.profile = result.profile  # type: ignore[misc]
        with pytest.raises(AttributeError):
            result.report.insights = ()  # type: ignore[misc]


class TestValidation:
    def test_missing_evidence(self) -> None:
        with pytest.raises(ResearchError, match="missing EvidenceReference"):
            ResearchAssembler().assemble(
                ResearchAssemblyContext(
                    identity=_identity(),
                    evidence_refs=(),
                    portfolio_ref=PortfolioReference(
                        portfolio_id="dsp.portfolio.demo"
                    ),
                )
            )

    def test_missing_identity_name(self) -> None:
        with pytest.raises(Exception):
            ResearchAssemblyContext(
                identity=ResearchIdentity(research_id="dsp.research.x", research_name=" "),
                evidence_refs=(_evidence(),),
            )

    def test_duplicate_decision_refs(self) -> None:
        pack = DecisionReference(
            instrument_symbol="AAA", digest="abcdef0123456789"
        )
        with pytest.raises(ResearchError, match="duplicate"):
            ResearchAssembler().assemble(
                ResearchAssemblyContext(
                    identity=_identity(),
                    evidence_refs=(_evidence(),),
                    decision_refs=(pack, pack),
                )
            )

    def test_foreign_monitoring(self) -> None:
        with pytest.raises(ResearchError, match="foreign ownership"):
            ResearchAssembler().assemble(
                ResearchAssemblyContext(
                    identity=_identity(),
                    evidence_refs=(_evidence(),),
                    portfolio_ref=PortfolioReference(
                        portfolio_id="dsp.portfolio.demo"
                    ),
                    monitoring_ref=MonitoringReference(
                        portfolio_id="dsp.portfolio.other"
                    ),
                )
            )

    def test_monitoring_without_portfolio(self) -> None:
        with pytest.raises(ResearchError, match="requires PortfolioReference"):
            ResearchAssembler().assemble(
                ResearchAssemblyContext(
                    identity=_identity(),
                    evidence_refs=(_evidence(),),
                    monitoring_ref=MonitoringReference(
                        portfolio_id="dsp.portfolio.demo"
                    ),
                )
            )

    def test_duplicate_research_id_in_many(self) -> None:
        with pytest.raises(ResearchError, match="duplicate"):
            ResearchAssembler().assemble_many((_ctx(), _ctx()))


class TestArchitectureAndCompatibility:
    def test_no_synthesis_in_assembler_source(self) -> None:
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "research"
            / "assembler.py"
        ).read_text(encoding="utf-8")
        assert "ResearchInsight(" not in source
        assert "ResearchConflict(" not in source
        assert "ResearchGap(" not in source
        assert "ResearchPriority(" not in source
        assert "Synthesizer" not in source or "deferred to ResearchSynthesizer" in source

    def test_backward_compatibility(self) -> None:
        import research as rs

        assert rs.ResearchIdentity is not None
        assert rs.ResearchAssembler is not None
        assert rs.ResearchAssemblyStatus.FAILED.value == "failed"
        assert rs.__version__ == "0.4.0"

    def test_platform_exports(self) -> None:
        import dsp_platform as platform

        assert platform.ResearchAssembler is ResearchAssembler
        assert platform.ResearchAssemblyStatus.PARTIAL.value == "partial"
