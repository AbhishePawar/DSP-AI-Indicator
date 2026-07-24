"""Recommendation Reporter tests (G1.3) — presentation only."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from recommendation import (
    AssemblyContext,
    ComparisonReference,
    DecisionReference,
    EngineContext,
    PortfolioReference,
    QuantitativeRiskReference,
    RecommendationAssembler,
    RecommendationEngine,
    RecommendationError,
    RecommendationIdentity,
    RecommendationReport,
    RecommendationReporter,
    RecommendationSummary,
    ReportingContext,
    ReportingStatus,
    ResearchReference,
    RiskReference,
    SignalPosture,
)


def _engine_result():
    assembly = RecommendationAssembler().assemble(
        AssemblyContext(
            identity=RecommendationIdentity(
                recommendation_id="dsp.recommendation.demo",
                recommendation_name="Demo Recommendation",
            ),
            decision_refs=(
                DecisionReference(
                    instrument_symbol="AAA", digest="abcdef0123456789"
                ),
            ),
            comparison_refs=(ComparisonReference(digest="abcdef0123456789"),),
            portfolio_ref=PortfolioReference(portfolio_id="dsp.portfolio.demo"),
            risk_refs=(RiskReference(risk_id="dsp.risk.demo"),),
            research_refs=(ResearchReference(research_id="dsp.research.demo"),),
            quantitative_risk_refs=(
                QuantitativeRiskReference(quantitative_risk_id="dsp.qrisk.demo"),
            ),
            as_of="2026-07-21",
        )
    )
    return RecommendationEngine().synthesize(
        EngineContext(
            assembly=assembly,
            qualitative_posture=SignalPosture.SUPPORTIVE,
            quantitative_posture=SignalPosture.SUPPORTIVE,
            valuation_posture=SignalPosture.SUPPORTIVE,
            portfolio_fit=SignalPosture.SUPPORTIVE,
            calculation_timestamp="2026-07-21T12:00:00Z",
        )
    )


class TestReporterHappyPath:
    def test_from_engine_result(self) -> None:
        engine_result = _engine_result()
        result = RecommendationReporter().report(engine_result)
        assert result.status is ReportingStatus.COMPLETE
        assert result.preferred_option is not None
        assert result.alternate_options
        assert result.scores
        assert result.rationales
        assert result.citation_sections
        assert result.metadata.option_count == 2
        assert "preferred" in result.summary_sections
        assert any("presentation only" in n for n in result.report.limitations)

    def test_from_report(self) -> None:
        engine_result = _engine_result()
        result = RecommendationReporter().report(engine_result.report)
        assert result.status is ReportingStatus.COMPLETE
        assert result.report.options == engine_result.report.options

    def test_preserves_decimal_identity(self) -> None:
        engine_result = _engine_result()
        source_values = {s.score_id: s.value for s in engine_result.scores}
        result = RecommendationReporter().report(
            ReportingContext(engine_result=engine_result)
        )
        for score in result.scores:
            assert score.value is source_values[score.score_id]

    def test_preserves_option_ordering(self) -> None:
        engine_result = _engine_result()
        result = RecommendationReporter().report(engine_result)
        assert result.report.options == engine_result.report.options

    def test_immutable(self) -> None:
        result = RecommendationReporter().report(_engine_result())
        with pytest.raises(AttributeError):
            result.report.options = ()  # type: ignore[misc]
        with pytest.raises(AttributeError):
            result.alternate_options = ()  # type: ignore[misc]


class TestReporterValidation:
    def test_missing_inputs(self) -> None:
        with pytest.raises(RecommendationError, match="missing report identity"):
            ReportingContext()

    def test_duplicate_summary_sections(self) -> None:
        with pytest.raises(RecommendationError, match="duplicate summary sections"):
            RecommendationReporter().report(
                ReportingContext(
                    engine_result=_engine_result(),
                    summary_sections=("overview", "Overview"),
                )
            )

    def test_identity_mismatch(self) -> None:
        engine_result = _engine_result()
        other = RecommendationReport(
            recommendation_id="dsp.recommendation.other",
            summary=RecommendationSummary(option_count=0),
            as_of="2026-07-21",
        )
        with pytest.raises(RecommendationError, match="duplicate recommendation ids"):
            RecommendationReporter().report(
                ReportingContext(engine_result=engine_result, report=other)
            )

    def test_report_many_duplicate(self) -> None:
        engine_result = _engine_result()
        with pytest.raises(RecommendationError, match="duplicate recommendation ids"):
            RecommendationReporter().report_many((engine_result, engine_result))


class TestReporterNoSynthesis:
    def test_no_engine_execution_imports(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "recommendation"
            / "reporter.py"
        ).read_text(encoding="utf-8")
        assert "RecommendationEngine" not in source
        assert "SignalPosture" not in source
        assert "quantize" not in source
        tree = ast.parse(source)
        forbidden = {"synthesize", "baseline", "optimize"}
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id.lower() in forbidden:
                found.add(node.id)
        assert found == set()
