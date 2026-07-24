"""Risk Reporter tests (E1.3)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from industry import EvidenceBundleReference, EvidenceBundleStatus
from portfolio import DecisionPackReference

from risk import (
    PortfolioReference,
    RiskAnalysisContext,
    RiskAnalyzer,
    RiskAssembler,
    RiskAssemblyContext,
    RiskAssessment,
    RiskCoverage,
    RiskCoverageKind,
    RiskCoverageStatus,
    RiskDescriptor,
    RiskError,
    RiskIdentity,
    RiskLevel,
    RiskObservation,
    RiskProfile,
    RiskReporter,
    RiskReportingContext,
    RiskReportingStatus,
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


def _analyzed_profile() -> RiskProfile:
    return RiskAnalyzer().analyze(_assembled_profile()).profile


def _empty_assessment(*, summary: RiskSummary | None = None) -> RiskAssessment:
    return RiskAssessment(
        assessment_id="dsp.risk.assessment.empty",
        risk_id="dsp.risk.demo",
        portfolio_id="dsp.portfolio.demo",
        as_of="2026-07-20",
        summary=summary,
    )


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


class TestReporting:
    def test_basic_reporting(self) -> None:
        profile = _analyzed_profile()
        result = RiskReporter().report(profile)
        assert result.report.risk_id == profile.identity.risk_id
        assert result.report.assessment_id is not None
        assert result.report.summary is not None
        assert result.report.observations

    def test_complete_reporting(self) -> None:
        analysis = RiskAnalyzer().analyze(_assembled_profile())
        result = RiskReporter().report(
            RiskReportingContext(
                profile=analysis.profile,
                assessment=analysis.assessment,
            )
        )
        assert result.status is RiskReportingStatus.COMPLETE
        assert result.report.observations
        assert result.report.descriptors
        assert result.report.coverage
        assert result.report.summary.observation_count > 0

    def test_partial_reporting(self) -> None:
        profile = _assembled_profile()
        result = RiskReporter().report(
            RiskReportingContext(
                profile=profile,
                assessment=_partial_assessment(),
            )
        )
        assert result.status is RiskReportingStatus.PARTIAL
        assert result.report.observations
        assert not result.report.descriptors
        assert result.warnings

    def test_empty_reporting(self) -> None:
        profile = _assembled_profile()
        result = RiskReporter().report(
            RiskReportingContext(
                profile=profile,
                assessment=_empty_assessment(
                    summary=RiskSummary(observation_count=0, descriptor_count=0)
                ),
            )
        )
        assert result.status is RiskReportingStatus.EMPTY
        assert not result.report.observations
        assert not result.report.descriptors
        assert not result.report.coverage


class TestValidation:
    def test_missing_assessment(self) -> None:
        with pytest.raises(RiskError, match="missing required artifacts: RiskAssessment"):
            RiskReporter().report(_assembled_profile())

    def test_missing_summary(self) -> None:
        with pytest.raises(RiskError, match="missing required artifacts: RiskSummary"):
            RiskReporter().report(
                RiskReportingContext(
                    profile=_assembled_profile(),
                    assessment=_empty_assessment(summary=None),
                )
            )

    def test_duplicate_sections(self) -> None:
        profile = _assembled_profile()
        assessment = RiskAssessment(
            assessment_id="dsp.risk.assessment.dup",
            risk_id="dsp.risk.demo",
            portfolio_id="dsp.portfolio.demo",
            as_of="2026-07-20",
            observations=(
                RiskObservation(code="same", text="Constraint posture is acceptable."),
            ),
            summary=RiskSummary(observation_count=1, descriptor_count=0),
        )
        with pytest.raises(RiskError, match="duplicate report sections"):
            RiskReporter().report(
                RiskReportingContext(
                    profile=profile,
                    assessment=assessment,
                    observations=(
                        RiskObservation(
                            code="same", text="Constraint posture is acceptable."
                        ),
                        RiskObservation(
                            code="same", text="Liquidity posture is acceptable."
                        ),
                    ),
                )
            )

    def test_ownership_validation(self) -> None:
        profile = _assembled_profile()
        foreign = RiskAssessment(
            assessment_id="dsp.risk.assessment.foreign",
            risk_id="dsp.risk.other",
            portfolio_id="dsp.portfolio.demo",
            as_of="2026-07-20",
            summary=RiskSummary(observation_count=0, descriptor_count=0),
        )
        with pytest.raises(RiskError, match="foreign ownership"):
            RiskReporter().report(
                RiskReportingContext(profile=profile, assessment=foreign)
            )

    def test_immutability(self) -> None:
        result = RiskReporter().report(_analyzed_profile())
        with pytest.raises(AttributeError):
            result.report = result.report  # type: ignore[misc]
        with pytest.raises(AttributeError):
            result.report.observations = ()  # type: ignore[misc]


class TestArchitectureAndCompatibility:
    def test_architecture_boundaries(self) -> None:
        reporting = (
            Path(__file__).resolve().parents[1] / "src" / "risk" / "reporting.py"
        )
        tree = ast.parse(reporting.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".", 1)[0])
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.add(node.module.split(".", 1)[0])
        assert "analyzer" not in imported
        assert "risk.analyzer" not in {
            (
                f"{node.module}"
                if isinstance(node, ast.ImportFrom) and node.module
                else ""
            )
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        }
        source = reporting.read_text(encoding="utf-8")
        assert "RiskAnalyzer" not in source
        assert "analyze(" not in source
        # No quantitative / recommendation vocabulary in reporter module.
        lowered = source.lower()
        for term in ("var", "sharpe", "beta", "buy", "sell", "optimize"):
            assert f'"{term}"' not in lowered
            assert f"'{term}'" not in lowered

    def test_backward_compatibility(self) -> None:
        import risk as rk

        assert rk.RiskAssembler is not None
        assert rk.RiskAnalyzer is not None
        assert rk.RiskReporter is not None
        assert rk.RiskReportingStatus.COMPLETE.value == "complete"
        assert rk.__version__ == "0.5.0"

        # Analyzer still produces a usable report; reporter re-presents it.
        analysis = RiskAnalyzer().analyze(
            RiskAnalysisContext(profile=_assembled_profile())
        )
        presented = RiskReporter().report(
            RiskReportingContext(
                profile=analysis.profile,
                assessment=analysis.assessment,
            )
        )
        assert presented.report.assessment_id == analysis.assessment.assessment_id
        assert len(presented.report.observations) == len(analysis.observations)

    def test_platform_exports(self) -> None:
        import dsp_platform as platform

        assert platform.RiskReporter is RiskReporter
        assert platform.RiskReportingStatus.PARTIAL.value == "partial"
        assert platform.RiskReportingContext is RiskReportingContext
        assert platform.RiskReportingResult is not None
