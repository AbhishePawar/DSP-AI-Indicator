"""Recommendation Engine tests (G1.2) — cite-backed synthesis only."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from recommendation import (
    AssemblyContext,
    AssemblyResult,
    ComparisonReference,
    ConfidenceLevel,
    ConflictSeverity,
    DecisionReference,
    EngineContext,
    EngineStatus,
    PortfolioReference,
    QuantitativeRiskReference,
    RecommendationAssembler,
    RecommendationEngine,
    RecommendationError,
    RecommendationIdentity,
    RecommendationType,
    ResearchReference,
    RiskReference,
    SignalPosture,
)


def _assemble() -> AssemblyResult:
    return RecommendationAssembler().assemble(
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


class TestEngineHappyPath:
    def test_supportive_baseline_buy(self) -> None:
        assembly = _assemble()
        result = RecommendationEngine().synthesize(
            EngineContext(
                assembly=assembly,
                qualitative_posture=SignalPosture.SUPPORTIVE,
                quantitative_posture=SignalPosture.SUPPORTIVE,
                valuation_posture=SignalPosture.SUPPORTIVE,
                portfolio_fit=SignalPosture.SUPPORTIVE,
                calculation_timestamp="2026-07-21T12:00:00Z",
            )
        )
        assert result.status is EngineStatus.COMPLETE
        assert result.preferred_option_id is not None
        preferred = next(
            o for o in result.options if o.option_id == result.preferred_option_id
        )
        assert preferred.option_type is RecommendationType.BUY
        assert result.scores[0].confidence_level is ConfidenceLevel.VERY_HIGH
        assert result.rationales
        assert all(o.supporting_report_refs for o in result.options)
        assert result.report.summary.option_count == 2

    def test_qual_vs_quant_conflict(self) -> None:
        result = RecommendationEngine().synthesize(
            EngineContext(
                assembly=_assemble(),
                qualitative_posture=SignalPosture.SUPPORTIVE,
                quantitative_posture=SignalPosture.ADVERSE,
                valuation_posture=SignalPosture.NEUTRAL,
                portfolio_fit=SignalPosture.NEUTRAL,
            )
        )
        assert any("qual_vs_quant" in c.conflict_id for c in result.conflicts)
        assert any(c.severity is ConflictSeverity.HIGH for c in result.conflicts)
        preferred = next(
            o for o in result.options if o.option_id == result.preferred_option_id
        )
        assert preferred.option_type is RecommendationType.HOLD
        assert result.scores[0].confidence_level is ConfidenceLevel.LOW

    def test_valuation_vs_portfolio_fit(self) -> None:
        result = RecommendationEngine().synthesize(
            EngineContext(
                assembly=_assemble(),
                qualitative_posture=SignalPosture.NEUTRAL,
                quantitative_posture=SignalPosture.NEUTRAL,
                valuation_posture=SignalPosture.SUPPORTIVE,
                portfolio_fit=SignalPosture.ADVERSE,
            )
        )
        assert any("valuation_vs_fit" in c.conflict_id for c in result.conflicts)
        preferred = next(
            o for o in result.options if o.option_id == result.preferred_option_id
        )
        assert preferred.option_type is RecommendationType.WATCH

    def test_insufficient_evidence(self) -> None:
        result = RecommendationEngine().synthesize(_assemble())
        preferred = next(
            o for o in result.options if o.option_id == result.preferred_option_id
        )
        assert preferred.option_type is RecommendationType.INSUFFICIENT_EVIDENCE
        assert any("insufficient" in c.conflict_id for c in result.conflicts)
        assert result.status is EngineStatus.PARTIAL

    def test_deterministic(self) -> None:
        ctx = EngineContext(
            assembly=_assemble(),
            qualitative_posture=SignalPosture.SUPPORTIVE,
            quantitative_posture=SignalPosture.CAUTIONARY,
            valuation_posture=SignalPosture.NEUTRAL,
            portfolio_fit=SignalPosture.NEUTRAL,
            calculation_timestamp="2026-07-21T12:00:00Z",
        )
        a = RecommendationEngine().synthesize(ctx)
        b = RecommendationEngine().synthesize(ctx)
        assert a.report.options == b.report.options
        assert a.report.scores == b.report.scores
        assert a.preferred_option_id == b.preferred_option_id

    def test_immutable(self) -> None:
        result = RecommendationEngine().synthesize(
            EngineContext(
                assembly=_assemble(),
                qualitative_posture=SignalPosture.SUPPORTIVE,
                quantitative_posture=SignalPosture.SUPPORTIVE,
                valuation_posture=SignalPosture.SUPPORTIVE,
                portfolio_fit=SignalPosture.SUPPORTIVE,
            )
        )
        with pytest.raises(AttributeError):
            result.report.options = ()  # type: ignore[misc]


class TestEngineValidation:
    def test_profile_mismatch(self) -> None:
        assembly = _assemble()
        other_assembly = RecommendationAssembler().assemble(
            AssemblyContext(
                identity=RecommendationIdentity(
                    recommendation_id="dsp.recommendation.other",
                    recommendation_name="Other",
                ),
                decision_refs=assembly.profile.decision_refs,
                comparison_refs=assembly.profile.comparison_refs,
                portfolio_ref=assembly.profile.portfolio_ref,  # type: ignore[arg-type]
                risk_refs=assembly.profile.risk_refs,
                research_refs=assembly.profile.research_refs,
                quantitative_risk_refs=assembly.profile.quantitative_risk_refs,
                as_of="2026-07-21",
            )
        )
        with pytest.raises(RecommendationError, match="broken references"):
            RecommendationEngine().synthesize(
                EngineContext(
                    assembly=assembly,
                    profile=other_assembly.profile,
                )
            )

    def test_duplicate_identities(self) -> None:
        assembly = _assemble()
        ctx = EngineContext(
            assembly=assembly,
            qualitative_posture=SignalPosture.NEUTRAL,
            quantitative_posture=SignalPosture.NEUTRAL,
            valuation_posture=SignalPosture.NEUTRAL,
            portfolio_fit=SignalPosture.NEUTRAL,
        )
        with pytest.raises(RecommendationError, match="duplicate identities"):
            RecommendationEngine().synthesize_many((ctx, ctx))


class TestEngineBoundaries:
    def test_no_mapper_or_upstream_engines(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "recommendation"
            / "engine.py"
        ).read_text(encoding="utf-8")
        assert "RecommendationMapper" not in source
        assert "from quantitative_risk" not in source
        assert "import quantitative_risk" not in source
        assert "ResearchSynthesizer" not in source
        tree = ast.parse(source)
        forbidden = {"optimize", "monte_carlo", "forecast"}
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id.lower() in forbidden:
                found.add(node.id)
        assert found == set()
