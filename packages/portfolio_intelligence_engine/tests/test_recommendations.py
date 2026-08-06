"""Tests for portfolio_intelligence_engine.recommendations."""

from __future__ import annotations

from portfolio_intelligence_engine import (
    HoldingSignal,
    RecommendationAction,
    generate_recommendations,
)


class TestGenerateRecommendations:
    def test_empty_holdings_returns_empty(self) -> None:
        assert generate_recommendations(()) == ()

    def test_watch_when_no_research_linked(self) -> None:
        holdings = (HoldingSignal(symbol="XYZ", weight=1.0),)
        recs = generate_recommendations(holdings)
        assert recs[0].action is RecommendationAction.WATCH

    def test_reduce_when_overvalued_and_concentrated(self) -> None:
        holdings = (HoldingSignal(symbol="AAPL", weight=0.5, margin_of_safety=-0.30),)
        recs = generate_recommendations(holdings)
        assert recs[0].action is RecommendationAction.REDUCE

    def test_review_when_overvalued_not_concentrated(self) -> None:
        holdings = (
            HoldingSignal(symbol="AAPL", weight=0.05, margin_of_safety=-0.30),
            HoldingSignal(symbol="MSFT", weight=0.95, margin_of_safety=0.0),
        )
        recs = generate_recommendations(holdings)
        aapl = next(r for r in recs if r.symbol == "AAPL")
        assert aapl.action is RecommendationAction.REVIEW

    def test_increase_when_undervalued_and_high_quality(self) -> None:
        holdings = (
            HoldingSignal(
                symbol="AAPL", weight=0.1, margin_of_safety=0.25, quality_score=80.0
            ),
        )
        recs = generate_recommendations(holdings)
        assert recs[0].action is RecommendationAction.INCREASE

    def test_review_when_undervalued_but_low_quality(self) -> None:
        holdings = (
            HoldingSignal(
                symbol="AAPL", weight=0.1, margin_of_safety=0.25, quality_score=30.0
            ),
        )
        recs = generate_recommendations(holdings)
        assert recs[0].action is RecommendationAction.REVIEW

    def test_hold_when_fairly_valued_no_flags(self) -> None:
        holdings = (
            HoldingSignal(
                symbol="AAPL", weight=0.1, margin_of_safety=0.0, quality_score=60.0
            ),
        )
        recs = generate_recommendations(holdings)
        assert recs[0].action is RecommendationAction.HOLD

    def test_watch_when_fairly_valued_but_hot_risk(self) -> None:
        holdings = (
            HoldingSignal(
                symbol="AAPL",
                weight=0.1,
                margin_of_safety=0.0,
                risk_contribution_pct=40.0,
            ),
        )
        recs = generate_recommendations(holdings)
        assert recs[0].action is RecommendationAction.WATCH

    def test_supporting_metrics_never_fabricated(self) -> None:
        holdings = (HoldingSignal(symbol="AAPL", weight=0.1, margin_of_safety=0.25),)
        recs = generate_recommendations(holdings)
        assert recs[0].supporting_metrics["quality_score"] is None
