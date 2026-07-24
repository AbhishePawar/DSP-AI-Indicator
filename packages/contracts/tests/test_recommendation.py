"""Tests for the Recommendation domain contract."""

from datetime import datetime

import pytest

from contracts.domain.evidence import Evidence
from contracts.domain.instrument import Instrument
from contracts.domain.recommendation import Recommendation
from contracts.enums import EngineSource, RecommendationAction
from contracts.exceptions import ContractValidationError


class TestRecommendation:
    """Tests for Recommendation construction and validation."""

    def test_minimal_recommendation(
        self, instrument: Instrument, utc_now: datetime
    ) -> None:
        recommendation = Recommendation(
            instrument=instrument,
            action=RecommendationAction.BUY,
            conviction=0.75,
            rationale="Strong fundamentals and favorable macro regime.",
            generated_at=utc_now,
        )
        assert recommendation.supporting_evidence == ()
        assert recommendation.dissenting_views == ()
        assert recommendation.time_horizon is None

    def test_full_recommendation(
        self, instrument: Instrument, utc_now: datetime
    ) -> None:
        evidence = Evidence(
            source_engine=EngineSource.VALUATION_ENGINE,
            claim="DCF fair value exceeds current price by 20%.",
        )
        recommendation = Recommendation(
            instrument=instrument,
            action=RecommendationAction.STRONG_BUY,
            conviction=0.9,
            rationale="Undervalued relative to intrinsic value with strong momentum.",
            generated_at=utc_now,
            supporting_evidence=[evidence],
            dissenting_views=["Macro risk agent flagged rate sensitivity."],
            time_horizon="12M",
            target_price=250.0,
        )
        assert recommendation.supporting_evidence == (evidence,)
        assert recommendation.dissenting_views == (
            "Macro risk agent flagged rate sensitivity.",
        )
        assert recommendation.target_price == 250.0

    def test_conviction_out_of_range_raises(
        self, instrument: Instrument, utc_now: datetime
    ) -> None:
        with pytest.raises(ContractValidationError, match="conviction"):
            Recommendation(
                instrument=instrument,
                action=RecommendationAction.HOLD,
                conviction=1.5,
                rationale="valid rationale",
                generated_at=utc_now,
            )

    def test_empty_rationale_raises(
        self, instrument: Instrument, utc_now: datetime
    ) -> None:
        with pytest.raises(ContractValidationError, match="rationale"):
            Recommendation(
                instrument=instrument,
                action=RecommendationAction.HOLD,
                conviction=0.5,
                rationale="   ",
                generated_at=utc_now,
            )

    def test_naive_generated_at_raises(self, instrument: Instrument) -> None:
        with pytest.raises(ContractValidationError, match="timezone-aware"):
            Recommendation(
                instrument=instrument,
                action=RecommendationAction.HOLD,
                conviction=0.5,
                rationale="valid rationale",
                generated_at=datetime(2026, 1, 1),
            )

    def test_immutable(self, instrument: Instrument, utc_now: datetime) -> None:
        recommendation = Recommendation(
            instrument=instrument,
            action=RecommendationAction.HOLD,
            conviction=0.5,
            rationale="valid rationale",
            generated_at=utc_now,
        )
        with pytest.raises(AttributeError):
            recommendation.conviction = 0.9  # type: ignore[misc]
