"""Business Quality scoring primitive tests."""

from __future__ import annotations

import pytest

from business_quality import (
    Assessment,
    Confidence,
    EvidenceLevel,
    Rating,
    RiskLevel,
    Score,
    WeightedScore,
    clip_score,
    score_from_mapping,
    weighted_mean,
)


class TestScoringPrimitives:
    def test_enums(self) -> None:
        assert Confidence.HIGH.value == "high"
        assert EvidenceLevel.NONE.value == "none"
        assert Rating.POOR.value == "poor"
        assert RiskLevel.ELEVATED.value == "elevated"

    def test_score_weighted_assessment(self) -> None:
        s = Score(value=80.0, unit="pts")
        w = WeightedScore(name="a", score=s, weight=0.5, contribution=40.0)
        a = Assessment(
            name="test",
            rating=Rating.STRONG,
            score=s,
            confidence=Confidence.HIGH,
            evidence_level=EvidenceLevel.STRONG,
            risk_level=RiskLevel.LOW,
            notes="n",
            components=(w,),
        )
        assert s.to_dict()["unit"] == "pts"
        assert w.to_dict()["weight"] == 0.5
        assert a.to_dict()["components"][0]["name"] == "a"
        assert Assessment(name="empty").to_dict()["score"] is None

    def test_helpers(self) -> None:
        assert clip_score(120.0) == 100.0
        assert clip_score(-5.0) == 0.0
        assert clip_score(50.0, lo=10.0, hi=40.0) == 40.0
        assert weighted_mean([(10.0, 1.0), (20.0, 1.0)]) == pytest.approx(15.0)
        assert weighted_mean([]) is None
        assert weighted_mean([(10.0, 0.0)]) is None
        assert weighted_mean([(10.0, -1.0), (20.0, 2.0)]) == pytest.approx(20.0)
        mapped = score_from_mapping({"value": 1.0, "unit": "x"})
        assert mapped.value == 1.0
        assert mapped.unit == "x"
        assert score_from_mapping({}).value is None
