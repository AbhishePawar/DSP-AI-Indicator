"""Business Quality model tests."""

from __future__ import annotations

from business_quality import (
    BUSINESS_QUALITY_VERSION,
    Assessment,
    BusinessQualityAnalysis,
    BusinessQualityFlag,
    BusinessQualityMetadata,
    BusinessQualityScore,
    BusinessQualitySummary,
    Confidence,
    Rating,
    Score,
    empty_validation,
)


class TestFlagsAndScores:
    def test_flag_values(self) -> None:
        assert BusinessQualityFlag.EXCELLENT.value == "excellent"
        assert BusinessQualityFlag.INSUFFICIENT_DATA.value == "insufficient_data"
        assert len(BusinessQualityFlag) == 7

    def test_score_and_summary_dicts(self) -> None:
        score = BusinessQualityScore(
            overall=Score(value=72.0),
            rating=Rating.STRONG,
            confidence=Confidence.MEDIUM,
            assessments=(
                Assessment(name="placeholder", rating=Rating.AVERAGE),
            ),
        )
        summary = BusinessQualitySummary(
            headline="shell",
            strengths=("a",),
            weaknesses=("b",),
            key_observations=("c",),
            flag=BusinessQualityFlag.AVERAGE,
        )
        assert score.to_dict()["rating"] == "strong"
        assert summary.to_dict()["flag"] == "average"

    def test_analysis_shell_dict(self) -> None:
        analysis = BusinessQualityAnalysis(
            metadata=BusinessQualityMetadata(
                engine_version=BUSINESS_QUALITY_VERSION,
                company="Acme",
                ticker="ACM",
            ),
            validation=empty_validation(),
            score=None,
            summary=BusinessQualitySummary(),
            quality_flags=(BusinessQualityFlag.UNKNOWN,),
            explainability=(),
            research_disclaimer="test",
        )
        payload = analysis.to_dict()
        assert payload["score"] is None
        assert payload["metadata"]["ticker"] == "ACM"
        assert payload["quality_flags"] == ["unknown"]
        assert analysis.metadata.to_dict()["schema_version"] == "1"
