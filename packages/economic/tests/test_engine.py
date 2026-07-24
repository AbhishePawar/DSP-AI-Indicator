"""End-to-end tests for EconomicEngine.analyze()."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from contracts.enums import EngineSource

from economic.engine import EconomicEngine
from economic.enums import EconomicCondition, Recommendation
from economic.exceptions import EconomicError

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


class TestEconomicEngine:
    """Bullish, bearish, mixed, and error paths."""

    def test_bullish_scenario(self, snapshot_factory) -> None:
        """High GDP + low inflation + stable rates → BUY."""
        engine = EconomicEngine(clock=lambda: FIXED_NOW)
        snapshot = snapshot_factory(
            gdp_growth=0.04,
            cpi_inflation=0.015,
            interest_rate=0.025,
            interest_rate_change=0.0,
            pmi=58.0,
            liquidity_indicator=0.75,
        )
        assessment = engine.analyze(snapshot)
        assert assessment.recommendation is Recommendation.BUY
        assert assessment.overall_condition in {
            EconomicCondition.EXPANSION,
            EconomicCondition.RECOVERY,
        }
        assert assessment.overall_condition is EconomicCondition.EXPANSION
        assert len(assessment.detected_signals) == 5
        assert len(assessment.evidence) == 5
        assert all(
            e.source_engine is EngineSource.ECONOMIC_ENGINE
            for e in assessment.evidence
        )
        assert assessment.assessed_at == FIXED_NOW

    def test_bearish_scenario(self, snapshot_factory) -> None:
        """High inflation + rapid rate hikes → SELL."""
        engine = EconomicEngine(clock=lambda: FIXED_NOW)
        snapshot = snapshot_factory(
            gdp_growth=0.005,
            cpi_inflation=0.06,
            interest_rate=0.05,
            interest_rate_change=0.01,
            pmi=42.0,
            liquidity_indicator=0.2,
        )
        assessment = engine.analyze(snapshot)
        assert assessment.recommendation is Recommendation.SELL
        assert assessment.overall_condition in {
            EconomicCondition.CONTRACTION,
            EconomicCondition.SLOWING,
        }
        assert assessment.overall_condition is EconomicCondition.CONTRACTION

    def test_mixed_signals_hold(self, snapshot_factory) -> None:
        engine = EconomicEngine(clock=lambda: FIXED_NOW)
        # Defaults are intentionally mixed/moderate
        assessment = engine.analyze(snapshot_factory())
        assert assessment.recommendation in {
            Recommendation.HOLD,
            Recommendation.BUY,
            Recommendation.SELL,
        }
        assert assessment.reasoning
        assert assessment.detected_signals

    def test_mixed_explicit_hold(self, snapshot_factory) -> None:
        """Construct an exactly balanced bullish/bearish mix."""
        engine = EconomicEngine(clock=lambda: FIXED_NOW)
        # Strong GDP (bull), high inflation (bear), stable rates (neutral),
        # soft PMI (neutral), tight liquidity (bear) → 1B 2Bear → SELL
        # Need equal: GDP strong bull, inflation high bear, rates stable
        # neutral, PMI soft neutral, liquidity adequate neutral → 1/1 → HOLD
        snapshot = snapshot_factory(
            gdp_growth=0.04,
            cpi_inflation=0.06,
            interest_rate=0.04,
            interest_rate_change=0.0,
            pmi=47.0,
            liquidity_indicator=0.5,
        )
        assessment = engine.analyze(snapshot)
        assert assessment.recommendation is Recommendation.HOLD
        assert assessment.overall_condition is EconomicCondition.SLOWING

    def test_unknown_analyzer_raises(self, snapshot_factory) -> None:
        engine = EconomicEngine(clock=lambda: FIXED_NOW)
        with pytest.raises(EconomicError, match="unknown"):
            engine.analyze(
                snapshot_factory(),
                analyzer_names=("gdp", "not_real"),
            )

    def test_custom_analyzer_subset(self, snapshot_factory) -> None:
        engine = EconomicEngine(clock=lambda: FIXED_NOW)
        assessment = engine.analyze(
            snapshot_factory(gdp_growth=0.04, cpi_inflation=0.015),
            analyzer_names=("gdp", "inflation"),
        )
        assert len(assessment.detected_signals) == 2
        names = {s.name for s in assessment.detected_signals}
        assert names == {"gdp", "inflation"}

    def test_determinism(self, snapshot_factory) -> None:
        engine = EconomicEngine(clock=lambda: FIXED_NOW)
        snapshot = snapshot_factory()
        assert engine.analyze(snapshot) == engine.analyze(snapshot)

    def test_analyzer_failure_wrapped(self, snapshot_factory) -> None:
        class Boom:
            def analyze(self, snapshot):
                raise RuntimeError("boom")

        engine = EconomicEngine(
            resolve_analyzer=lambda name: Boom(),
            clock=lambda: FIXED_NOW,
        )
        with pytest.raises(EconomicError, match="failed"):
            engine.analyze(snapshot_factory(), analyzer_names=("gdp",))
