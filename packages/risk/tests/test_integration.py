"""Risk Integrator tests (E1.4)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from industry import EvidenceBundleReference, EvidenceBundleStatus
from portfolio import DecisionPackReference

from risk import (
    PortfolioReference,
    RiskAnalyzer,
    RiskAssembler,
    RiskAssemblyContext,
    RiskAssessment,
    RiskCoverage,
    RiskCoverageKind,
    RiskCoverageStatus,
    RiskError,
    RiskIdentity,
    RiskIntegrationContext,
    RiskIntegrationStatus,
    RiskIntegrator,
    RiskObservation,
    RiskProfile,
    RiskReport,
    RiskReporter,
    RiskReportingContext,
    RiskSummary,
)


def _pack(symbol: str) -> DecisionPackReference:
    return DecisionPackReference(instrument_symbol=symbol, digest="abcdef0123456789")


def _assembled_profile() -> RiskProfile:
    return RiskAssembler().assemble(
        RiskAssemblyContext(
            identity=RiskIdentity(risk_id="dsp.risk.demo", risk_name="Demo"),
            portfolio_ref=PortfolioReference(portfolio_id="dsp.portfolio.demo"),
            decision_pack_refs=(_pack("AAA"), _pack("BBB")),
            evidence_bundle_refs=(
                EvidenceBundleReference(
                    bundle_id="dsp.evidence_bundle.aaa",
                    instrument_key="AAA",
                    methodology_id="dsp.methodology.commercial_banking",
                    methodology_version="1.0.0",
                    digest="abcdef0123456789deadbeef",
                    status=EvidenceBundleStatus.INCOMPLETE,
                ),
            ),
        )
    ).profile


def _analyzed() -> tuple[RiskProfile, RiskAssessment, RiskReport]:
    analysis = RiskAnalyzer().analyze(_assembled_profile())
    return analysis.profile, analysis.assessment, analysis.report


def _partial_assessment() -> RiskAssessment:
    return RiskAssessment(
        assessment_id="dsp.risk.assessment.partial",
        risk_id="dsp.risk.demo",
        portfolio_id="dsp.portfolio.demo",
        as_of="2026-07-20",
        observations=(
            RiskObservation(
                code="coverage_note",
                text="Decision coverage is present for cited packs.",
            ),
        ),
        coverage=(
            RiskCoverage(
                kind=RiskCoverageKind.DECISION,
                status=RiskCoverageStatus.PARTIAL,
                label="Decision coverage is partial.",
            ),
        ),
        summary=RiskSummary(
            observation_count=1,
            descriptor_count=0,
            coverage_notes=("Decision citations are present.",),
        ),
    )


class TestIntegration:
    def test_basic_integration(self) -> None:
        profile, assessment, report = _analyzed()
        # Report from analysis — not re-passing assessment (already on profile).
        result = RiskIntegrator().integrate(
            RiskIntegrationContext(profile=profile, report=report)
        )
        assert result.status is RiskIntegrationStatus.COMPLETE
        assert result.context.assessment is not None
        assert result.context.assessment.assessment_id == assessment.assessment_id
        assert result.context.report is report
        assert result.context.summary is not None
        assert result.context.coverage
        assert result.context.reporting_inputs_ready is True
        assert result.context.monitoring_inputs_ready is True

    def test_partial_integration(self) -> None:
        result = RiskIntegrator().integrate(
            RiskIntegrationContext(
                profile=_assembled_profile(),
                assessment=_partial_assessment(),
            )
        )
        assert result.status is RiskIntegrationStatus.PARTIAL
        assert result.context.assessment is not None
        assert result.context.report is None
        assert result.context.reporting_inputs_ready is True
        assert result.warnings


class TestValidation:
    def test_duplicate_artifacts(self) -> None:
        profile, assessment, _report = _analyzed()
        with pytest.raises(RiskError, match="duplicate artifacts"):
            RiskIntegrator().integrate(
                RiskIntegrationContext(profile=profile, assessment=assessment)
            )

    def test_ownership(self) -> None:
        profile = _assembled_profile()
        foreign = RiskAssessment(
            assessment_id="dsp.risk.assessment.foreign",
            risk_id="dsp.risk.other",
            portfolio_id="dsp.portfolio.demo",
            as_of="2026-07-20",
            summary=RiskSummary(observation_count=0, descriptor_count=0),
        )
        with pytest.raises(RiskError, match="foreign ownership"):
            RiskIntegrator().integrate(
                RiskIntegrationContext(profile=profile, assessment=foreign)
            )

    def test_reference_validation(self) -> None:
        profile = _assembled_profile()
        assessment = _partial_assessment()
        report = RiskReport(
            risk_id="dsp.risk.demo",
            portfolio_id="dsp.portfolio.demo",
            summary=assessment.summary or RiskSummary(0, 0),
            assessment_id="dsp.risk.assessment.mismatch",
        )
        with pytest.raises(RiskError, match="broken references"):
            RiskIntegrator().integrate(
                RiskIntegrationContext(
                    profile=profile,
                    assessment=assessment,
                    report=report,
                )
            )

    def test_immutability(self) -> None:
        profile, _assessment, report = _analyzed()
        result = RiskIntegrator().integrate(
            RiskIntegrationContext(profile=profile, report=report)
        )
        with pytest.raises(AttributeError):
            result.context = result.context  # type: ignore[misc]
        with pytest.raises(AttributeError):
            result.context.coverage = ()  # type: ignore[misc]


class TestArchitectureAndCompatibility:
    def test_architecture_boundaries(self) -> None:
        path = Path(__file__).resolve().parents[1] / "src" / "risk" / "integration.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.add(node.module)
        assert "risk.analyzer" not in imported
        assert "risk.reporting" not in imported
        assert "RiskAnalyzer" not in source
        assert "RiskReporter" not in source
        assert "analyze(" not in source
        assert "PortfolioMonitor" not in source
        lowered = source.lower()
        for term in ("var", "sharpe", "beta", "buy", "sell", "optimize"):
            assert f'"{term}"' not in lowered
            assert f"'{term}'" not in lowered

    def test_backward_compatibility(self) -> None:
        import risk as rk

        assert rk.RiskAssembler is not None
        assert rk.RiskAnalyzer is not None
        assert rk.RiskReporter is not None
        assert rk.RiskIntegrator is not None
        assert rk.IntegratedRiskContext is not None
        assert rk.RiskIntegrationStatus.COMPLETE.value == "complete"
        assert rk.__version__ == "0.5.0"

        # Prior layers still compose: analyze → report → integrate.
        analysis = RiskAnalyzer().analyze(_assembled_profile())
        presented = RiskReporter().report(
            RiskReportingContext(
                profile=analysis.profile,
                assessment=analysis.assessment,
            )
        )
        integrated = RiskIntegrator().integrate(
            RiskIntegrationContext(
                profile=analysis.profile,
                report=presented.report,
            )
        )
        assert integrated.status is RiskIntegrationStatus.COMPLETE
        assert (
            integrated.context.report.assessment_id
            == analysis.assessment.assessment_id
        )

    def test_platform_exports(self) -> None:
        import dsp_platform as platform

        assert platform.RiskIntegrator is RiskIntegrator
        assert platform.RiskIntegrationStatus.PARTIAL.value == "partial"
        assert platform.IntegratedRiskContext is not None
        assert platform.RiskIntegrationContext is RiskIntegrationContext
