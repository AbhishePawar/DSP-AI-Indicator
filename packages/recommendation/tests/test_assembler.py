"""Recommendation Assembler tests (G1.1) — construction only."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from core.exceptions import ValidationError

from recommendation import (
    AssemblyContext,
    AssemblyStatus,
    ComparisonReference,
    DecisionReference,
    PortfolioReference,
    QuantitativeRiskReference,
    RecommendationAssembler,
    RecommendationError,
    RecommendationIdentity,
    ResearchReference,
    RiskReference,
)


def _identity(
    recommendation_id: str = "dsp.recommendation.demo",
) -> RecommendationIdentity:
    return RecommendationIdentity(
        recommendation_id=recommendation_id,
        recommendation_name="Demo Recommendation",
    )


def _ctx(
    *,
    recommendation_id: str = "dsp.recommendation.demo",
    as_of: str | None = "2026-07-21",
    decision_refs: tuple[DecisionReference, ...] | None = None,
    comparison_refs: tuple[ComparisonReference, ...] | None = None,
    include_portfolio: bool = True,
    risk_refs: tuple[RiskReference, ...] | None = None,
    research_refs: tuple[ResearchReference, ...] | None = None,
    quantitative_risk_refs: tuple[QuantitativeRiskReference, ...] | None = None,
) -> AssemblyContext:
    kwargs: dict = {
        "identity": _identity(recommendation_id),
        "decision_refs": (
            (
                DecisionReference(
                    instrument_symbol="AAA", digest="abcdef0123456789"
                ),
            )
            if decision_refs is None
            else decision_refs
        ),
        "comparison_refs": (
            (ComparisonReference(digest="abcdef0123456789"),)
            if comparison_refs is None
            else comparison_refs
        ),
        "risk_refs": (
            (RiskReference(risk_id="dsp.risk.demo"),)
            if risk_refs is None
            else risk_refs
        ),
        "research_refs": (
            (ResearchReference(research_id="dsp.research.demo"),)
            if research_refs is None
            else research_refs
        ),
        "quantitative_risk_refs": (
            (QuantitativeRiskReference(quantitative_risk_id="dsp.qrisk.demo"),)
            if quantitative_risk_refs is None
            else quantitative_risk_refs
        ),
        "as_of": as_of,
    }
    if include_portfolio:
        kwargs["portfolio_ref"] = PortfolioReference(
            portfolio_id="dsp.portfolio.demo"
        )
    return AssemblyContext(**kwargs)


class TestAssemblyHappyPath:
    def test_complete_skeleton(self) -> None:
        result = RecommendationAssembler().assemble(_ctx())
        assert result.status is AssemblyStatus.COMPLETE
        assert result.profile.recommendation_id == "dsp.recommendation.demo"
        assert result.profile.options == ()
        assert result.profile.scores == ()
        assert result.profile.rationales == ()
        assert result.profile.conflicts == ()
        assert result.profile.summary is not None
        assert result.profile.summary.option_count == 0
        assert result.report.options == ()
        assert result.report.portfolio_ref is not None
        assert result.report.decision_refs
        assert result.report.research_refs
        assert result.report.quantitative_risk_refs
        assert any("skeleton" in note.lower() for note in result.report.limitations)

    def test_partial_without_as_of(self) -> None:
        result = RecommendationAssembler().assemble(_ctx(as_of=None))
        assert result.status is AssemblyStatus.PARTIAL
        assert result.report.as_of == "unknown"
        assert result.warnings

    def test_immutable_output(self) -> None:
        result = RecommendationAssembler().assemble(_ctx())
        with pytest.raises(AttributeError):
            result.report.options = ()  # type: ignore[misc]


class TestAssemblyValidation:
    def test_missing_decision(self) -> None:
        with pytest.raises(RecommendationError, match="missing Decision"):
            RecommendationAssembler().assemble(_ctx(decision_refs=()))

    def test_missing_comparison(self) -> None:
        with pytest.raises(RecommendationError, match="missing Comparison"):
            RecommendationAssembler().assemble(_ctx(comparison_refs=()))

    def test_missing_portfolio(self) -> None:
        with pytest.raises(TypeError):
            # portfolio_ref is a required dataclass field
            _ctx(include_portfolio=False)

    def test_missing_risk(self) -> None:
        with pytest.raises(RecommendationError, match="missing Risk"):
            RecommendationAssembler().assemble(_ctx(risk_refs=()))

    def test_missing_research(self) -> None:
        with pytest.raises(RecommendationError, match="missing Research"):
            RecommendationAssembler().assemble(_ctx(research_refs=()))

    def test_missing_quantitative_risk(self) -> None:
        with pytest.raises(RecommendationError, match="missing Quantitative Risk"):
            RecommendationAssembler().assemble(_ctx(quantitative_risk_refs=()))

    def test_duplicate_decision(self) -> None:
        ref = DecisionReference(instrument_symbol="AAA", digest="abcdef0123456789")
        with pytest.raises(RecommendationError, match="duplicate report references"):
            RecommendationAssembler().assemble(_ctx(decision_refs=(ref, ref)))

    def test_foreign_ownership_symbols(self) -> None:
        with pytest.raises(RecommendationError, match="foreign ownership"):
            RecommendationAssembler().assemble(
                _ctx(
                    decision_refs=(
                        DecisionReference(
                            instrument_symbol="AAA", digest="abcdef0123456789"
                        ),
                        DecisionReference(
                            instrument_symbol="BBB", digest="abcdef0123456790"
                        ),
                    )
                )
            )

    def test_duplicate_identities_assemble_many(self) -> None:
        ctx = _ctx()
        with pytest.raises(RecommendationError, match="duplicate identities"):
            RecommendationAssembler().assemble_many((ctx, ctx))

    def test_explicit_none_portfolio_rejected(self) -> None:
        with pytest.raises(ValidationError, match="portfolio_ref"):
            AssemblyContext(
                identity=_identity(),
                decision_refs=(
                    DecisionReference(
                        instrument_symbol="AAA", digest="abcdef0123456789"
                    ),
                ),
                comparison_refs=(ComparisonReference(digest="abcdef0123456789"),),
                portfolio_ref=None,  # type: ignore[arg-type]
                risk_refs=(RiskReference(risk_id="dsp.risk.demo"),),
                research_refs=(ResearchReference(research_id="dsp.research.demo"),),
                quantitative_risk_refs=(
                    QuantitativeRiskReference(quantitative_risk_id="dsp.qrisk.demo"),
                ),
            )


class TestAssemblerNoSynthesis:
    def test_no_mapper_import(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "recommendation"
            / "assembler.py"
        ).read_text(encoding="utf-8")
        assert "RecommendationMapper" not in source
        assert "mapper" not in source

    def test_no_scoring_ops(self) -> None:
        path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "recommendation"
            / "assembler.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        forbidden = {"RecommendationOption", "RecommendationScore", "Decimal"}
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden:
                found.add(node.id)
        assert found == set()
