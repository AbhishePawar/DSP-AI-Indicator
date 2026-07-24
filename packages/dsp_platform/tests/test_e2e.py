"""Offline end-to-end tests through DSPPlatform.analyze()."""

from __future__ import annotations

from datetime import date
from typing import Callable

import pytest

from contracts.domain.instrument import Instrument
from contracts.domain.recommendation import Recommendation
from contracts.enums import RecommendationAction, SignalDirection
from data_engine.exceptions import DataEngineError
from dsp_platform import (
    DSPPlatform,
    Environment,
    PlatformConfig,
    PlatformError,
    PlatformSecrets,
    ProviderSettings,
)
from economic.enums import Recommendation as EcoRecommendation
from orchestration.exceptions import OrchestrationError
from snapshot_bridge.exceptions import SnapshotBridgeError

BuildPlatform = Callable[..., DSPPlatform]


class TestRecommendationOutcomes:
    def test_buy_recommendation(
        self, instrument: Instrument, build_platform: BuildPlatform
    ) -> None:
        platform = build_platform()
        request = platform.make_request(
            instrument, date(2024, 1, 1), date(2024, 6, 1)
        )
        result = platform.analyze(request)
        assert isinstance(result, Recommendation)
        assert result.action is RecommendationAction.BUY
        assert result.instrument == instrument
        assert 0.0 <= result.conviction <= 1.0

    def test_sell_recommendation(
        self, instrument: Instrument, build_platform: BuildPlatform
    ) -> None:
        platform = build_platform(
            technical=SignalDirection.BEARISH,
            fundamental=SignalDirection.BEARISH,
            economic=EcoRecommendation.SELL,
        )
        result = platform.analyze(
            platform.make_request(instrument, date(2024, 1, 1), date(2024, 6, 1))
        )
        assert result.action is RecommendationAction.SELL

    def test_hold_recommendation(
        self, instrument: Instrument, build_platform: BuildPlatform
    ) -> None:
        platform = build_platform(
            technical=SignalDirection.NEUTRAL,
            fundamental=SignalDirection.NEUTRAL,
            economic=EcoRecommendation.HOLD,
        )
        result = platform.analyze(
            platform.make_request(instrument, date(2024, 1, 1), date(2024, 6, 1))
        )
        assert result.action is RecommendationAction.HOLD

    def test_committee_disagreement_maps_to_hold(
        self, instrument: Instrument, build_platform: BuildPlatform
    ) -> None:
        # BUY vs SELL plurality tie with HOLD votes → Decision.NEUTRAL → HOLD
        platform = build_platform(
            technical=SignalDirection.BULLISH,
            fundamental=SignalDirection.BEARISH,
            economic=EcoRecommendation.HOLD,
            valuation_mos=None,  # valuation HOLDs when MoS unavailable
        )
        result = platform.analyze(
            platform.make_request(instrument, date(2024, 1, 1), date(2024, 6, 1))
        )
        assert result.action is RecommendationAction.HOLD
        assert result.conviction == pytest.approx(0.5)


class TestPartialAndMissing:
    def test_partial_economic_data_allow_partial(
        self, instrument: Instrument, build_platform: BuildPlatform
    ) -> None:
        platform = build_platform(
            eco_error=SnapshotBridgeError("partial series unavailable"),
        )
        request = platform.make_request(
            instrument,
            date(2024, 1, 1),
            date(2024, 6, 1),
            allow_partial=True,
        )
        result = platform.analyze(request)
        assert isinstance(result, Recommendation)
        assert result.action is RecommendationAction.BUY

    def test_missing_fundamentals_allow_partial(
        self, instrument: Instrument, build_platform: BuildPlatform
    ) -> None:
        platform = build_platform(
            fund_error=SnapshotBridgeError("fundamentals missing"),
        )
        request = platform.make_request(
            instrument,
            date(2024, 1, 1),
            date(2024, 6, 1),
            allow_partial=True,
        )
        result = platform.analyze(request)
        assert isinstance(result, Recommendation)

    def test_missing_fundamentals_strict_raises(
        self, instrument: Instrument, build_platform: BuildPlatform
    ) -> None:
        platform = build_platform(
            fund_error=SnapshotBridgeError("fundamentals missing"),
        )
        request = platform.make_request(
            instrument,
            date(2024, 1, 1),
            date(2024, 6, 1),
            allow_partial=False,
        )
        with pytest.raises(PlatformError, match="platform analysis failed"):
            platform.analyze(request)


class TestFailuresAndErrors:
    def test_provider_failure_becomes_platform_error(
        self, instrument: Instrument, build_platform: BuildPlatform
    ) -> None:
        platform = build_platform(
            market_error=DataEngineError("provider down"),
        )
        with pytest.raises(PlatformError) as exc_info:
            platform.analyze(
                platform.make_request(
                    instrument, date(2024, 1, 1), date(2024, 6, 1)
                )
            )
        assert not isinstance(exc_info.value, DataEngineError)
        assert not isinstance(exc_info.value, OrchestrationError)

    def test_configuration_failure(self) -> None:
        config = PlatformConfig(
            environment=Environment.PRODUCTION,
            providers=ProviderSettings(enable_economic=True),
            secrets=PlatformSecrets(fred_api_key=None),
        )
        with pytest.raises(PlatformError, match="fred_api_key"):
            DSPPlatform.from_config(config)


class TestDeterminismAndPublicOutput:
    def test_deterministic_recommendations(
        self, instrument: Instrument, build_platform: BuildPlatform
    ) -> None:
        platform = build_platform()
        request = platform.make_request(
            instrument, date(2024, 1, 1), date(2024, 6, 1)
        )
        first = platform.analyze(request)
        second = platform.analyze(request)
        assert first.action is second.action
        assert first.conviction == second.conviction
        assert first.rationale == second.rationale

    def test_public_recommendation_shape(
        self, instrument: Instrument, build_platform: BuildPlatform
    ) -> None:
        platform = build_platform()
        result = platform.analyze(
            platform.make_request(instrument, date(2024, 1, 1), date(2024, 6, 1))
        )
        assert result.instrument.symbol == "AAPL"
        assert isinstance(result.rationale, str)
        assert result.rationale
        assert result.generated_at is not None
