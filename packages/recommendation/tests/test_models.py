"""Recommendation domain model tests (G1.0)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from core.exceptions import ValidationError

from recommendation import (
    ComparisonReference,
    ConfidenceLevel,
    ConflictSeverity,
    DecisionReference,
    PortfolioReference,
    QuantitativeRiskReference,
    RecommendationConflict,
    RecommendationError,
    RecommendationIdentity,
    RecommendationOption,
    RecommendationProfile,
    RecommendationRationale,
    RecommendationReport,
    RecommendationScore,
    RecommendationSummary,
    RecommendationType,
    ResearchReference,
    RiskReference,
)


def _identity() -> RecommendationIdentity:
    return RecommendationIdentity(
        recommendation_id="dsp.recommendation.demo",
        recommendation_name="Demo Recommendation",
        created_at="2026-07-21T00:00:00Z",
    )


def _score(*, score_id: str = "dsp.recommendation.score.conf") -> RecommendationScore:
    return RecommendationScore(
        score_id=score_id,
        score_type="confidence",
        value=Decimal("0.72"),
        unit="confidence_fraction",
        method_id="dsp.recommendation.method.confidence.v1",
        provenance=("research:dsp.research.demo",),
        calculation_timestamp="2026-07-21T12:00:00Z",
        confidence_level=ConfidenceLevel.HIGH,
    )


def _rationale(
    *, rationale_id: str = "dsp.recommendation.rationale.1"
) -> RecommendationRationale:
    return RecommendationRationale(
        rationale_id=rationale_id,
        title="Research supports hold",
        body="Cited research coverage remains incomplete for aggressive add.",
        supporting_report_refs=("research:dsp.research.demo",),
    )


def _refs() -> dict:
    decision = DecisionReference(
        instrument_symbol="AAA", digest="abcdef0123456789"
    )
    comparison = ComparisonReference(digest="abcdef0123456789")
    portfolio = PortfolioReference(portfolio_id="dsp.portfolio.demo")
    risk = RiskReference(risk_id="dsp.risk.demo")
    research = ResearchReference(research_id="dsp.research.demo")
    quant = QuantitativeRiskReference(quantitative_risk_id="dsp.qrisk.demo")
    return {
        "decision": decision,
        "comparison": comparison,
        "portfolio": portfolio,
        "risk": risk,
        "research": research,
        "quant": quant,
    }


def _option(
    *,
    option_id: str = "dsp.recommendation.option.hold",
    option_type: RecommendationType = RecommendationType.HOLD,
    score_id: str = "dsp.recommendation.score.conf",
    rationale_id: str = "dsp.recommendation.rationale.1",
) -> RecommendationOption:
    return RecommendationOption(
        option_id=option_id,
        option_type=option_type,
        title="Hold posture",
        description="Maintain current exposure pending further research.",
        supporting_rationale_refs=(rationale_id,),
        supporting_report_refs=(
            "research:dsp.research.demo",
            "risk:dsp.risk.demo",
            "quantitative_risk:dsp.qrisk.demo",
        ),
        confidence_reference=score_id,
        priority=1,
    )


class TestConstruction:
    def test_profile_and_report(self) -> None:
        refs = _refs()
        score = _score()
        rationale = _rationale()
        option = _option()
        conflict = RecommendationConflict(
            conflict_id="dsp.recommendation.conflict.1",
            title="Qual vs Quant tension",
            description="Qualitative watch posture vs elevated drawdown metric.",
            severity=ConflictSeverity.MEDIUM,
            option_refs=(option.option_id,),
            report_refs=(
                "risk:dsp.risk.demo",
                "quantitative_risk:dsp.qrisk.demo",
            ),
        )
        profile = RecommendationProfile(
            identity=_identity(),
            decision_refs=(refs["decision"],),
            comparison_refs=(refs["comparison"],),
            portfolio_ref=refs["portfolio"],
            risk_refs=(refs["risk"],),
            research_refs=(refs["research"],),
            quantitative_risk_refs=(refs["quant"],),
            options=(option,),
            scores=(score,),
            rationales=(rationale,),
            conflicts=(conflict,),
            summary=RecommendationSummary(
                option_count=1,
                conflict_count=1,
                rationale_count=1,
                score_count=1,
            ),
            preferred_option_id=option.option_id,
        )
        assert profile.recommendation_id == "dsp.recommendation.demo"

        report = RecommendationReport(
            recommendation_id="dsp.recommendation.demo",
            summary=profile.summary,  # type: ignore[arg-type]
            as_of="2026-07-21",
            options=(option,),
            scores=(score,),
            rationales=(rationale,),
            conflicts=(conflict,),
            decision_refs=(refs["decision"],),
            comparison_refs=(refs["comparison"],),
            portfolio_ref=refs["portfolio"],
            risk_refs=(refs["risk"],),
            research_refs=(refs["research"],),
            quantitative_risk_refs=(refs["quant"],),
            preferred_option_id=option.option_id,
            limitations=("Contracts only — no engine.",),
        )
        assert report.preferred_option_id == option.option_id
        with pytest.raises(AttributeError):
            report.options = ()  # type: ignore[misc]

    def test_legacy_mapper_still_exported(self) -> None:
        from recommendation import RecommendationMapper

        assert RecommendationMapper is not None


class TestValidation:
    def test_reject_float_score(self) -> None:
        with pytest.raises(ValidationError, match="decimal.Decimal"):
            RecommendationScore(
                score_id="dsp.recommendation.score.x",
                score_type="confidence",
                value=0.5,  # type: ignore[arg-type]
                unit="confidence_fraction",
                method_id="dsp.recommendation.method.x",
                provenance=("p",),
                calculation_timestamp="2026-07-21T00:00:00Z",
            )

    def test_missing_method_unit_provenance(self) -> None:
        with pytest.raises(ValidationError, match="method_id"):
            RecommendationScore(
                score_id="dsp.recommendation.score.x",
                score_type="confidence",
                value=Decimal("0.5"),
                unit="confidence_fraction",
                method_id=" ",
                provenance=("p",),
                calculation_timestamp="2026-07-21T00:00:00Z",
            )
        with pytest.raises(ValidationError, match="unit"):
            RecommendationScore(
                score_id="dsp.recommendation.score.x",
                score_type="confidence",
                value=Decimal("0.5"),
                unit=" ",
                method_id="dsp.recommendation.method.x",
                provenance=("p",),
                calculation_timestamp="2026-07-21T00:00:00Z",
            )
        with pytest.raises(RecommendationError, match="provenance"):
            RecommendationScore(
                score_id="dsp.recommendation.score.x",
                score_type="confidence",
                value=Decimal("0.5"),
                unit="confidence_fraction",
                method_id="dsp.recommendation.method.x",
                provenance=(),
                calculation_timestamp="2026-07-21T00:00:00Z",
            )

    def test_duplicate_options(self) -> None:
        refs = _refs()
        option = _option()
        with pytest.raises(RecommendationError, match="duplicate options"):
            RecommendationProfile(
                identity=_identity(),
                research_refs=(refs["research"],),
                risk_refs=(refs["risk"],),
                quantitative_risk_refs=(refs["quant"],),
                options=(option, option),
                scores=(_score(),),
                rationales=(_rationale(),),
            )

    def test_broken_rationale_ref(self) -> None:
        refs = _refs()
        with pytest.raises(RecommendationError, match="broken rationale"):
            RecommendationProfile(
                identity=_identity(),
                research_refs=(refs["research"],),
                risk_refs=(refs["risk"],),
                quantitative_risk_refs=(refs["quant"],),
                options=(_option(rationale_id="dsp.recommendation.rationale.missing"),),
                scores=(_score(),),
                rationales=(_rationale(),),
            )

    def test_broken_report_ref(self) -> None:
        with pytest.raises(RecommendationError, match="broken report references"):
            RecommendationProfile(
                identity=_identity(),
                options=(
                    RecommendationOption(
                        option_id="dsp.recommendation.option.hold",
                        option_type=RecommendationType.HOLD,
                        title="Hold",
                        description="Hold",
                        supporting_rationale_refs=("dsp.recommendation.rationale.1",),
                        supporting_report_refs=("research:missing",),
                        confidence_reference="dsp.recommendation.score.conf",
                        priority=0,
                    ),
                ),
                scores=(_score(),),
                rationales=(
                    RecommendationRationale(
                        rationale_id="dsp.recommendation.rationale.1",
                        title="R",
                        body="Body text for rationale.",
                    ),
                ),
            )

    def test_broken_conflict_option_ref(self) -> None:
        refs = _refs()
        with pytest.raises(RecommendationError, match="broken conflict"):
            RecommendationProfile(
                identity=_identity(),
                research_refs=(refs["research"],),
                risk_refs=(refs["risk"],),
                quantitative_risk_refs=(refs["quant"],),
                options=(_option(),),
                scores=(_score(),),
                rationales=(_rationale(),),
                conflicts=(
                    RecommendationConflict(
                        conflict_id="dsp.recommendation.conflict.x",
                        title="X",
                        description="X",
                        severity=ConflictSeverity.LOW,
                        option_refs=("dsp.recommendation.option.missing",),
                    ),
                ),
            )

    def test_empty_identity(self) -> None:
        with pytest.raises(ValidationError):
            RecommendationIdentity(
                recommendation_id=" ",
                recommendation_name="Demo",
            )


class TestPlatformExport:
    def test_platform_exports(self) -> None:
        import dsp_platform as platform

        assert platform.RecommendationIdentity is RecommendationIdentity
        assert platform.RecommendationType.HOLD.value == "hold"
        assert platform.RecommendationMapper is not None
        assert platform.RecommendationAssembler is not None
        assert platform.AssemblyStatus.COMPLETE.value == "complete"
        assert platform.RecommendationEngine is not None
        assert platform.EngineStatus.COMPLETE.value == "complete"
        assert platform.RecommendationReporter is not None
        assert platform.ReportingStatus.COMPLETE.value == "complete"
