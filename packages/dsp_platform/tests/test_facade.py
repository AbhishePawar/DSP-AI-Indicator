"""Tests for DSPPlatform façade."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest

from contracts.domain.instrument import Instrument
from contracts.domain.recommendation import Recommendation
from contracts.enums import AssetClass, RecommendationAction
from dsp_platform import (
    AnalysisRequest,
    DSPPlatform,
    Environment,
    FeatureFlags,
    PlatformConfig,
    PlatformError,
    PlatformSecrets,
    ProviderSettings,
)
from orchestration.exceptions import OrchestrationError

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")


class _FakeAnalysisService:
    def __init__(
        self,
        recommendation: Recommendation | None = None,
        *,
        report: Any | None = None,
        error: Exception | None = None,
    ) -> None:
        self._recommendation = recommendation
        self._report = report
        self._error = error
        self.calls = 0
        self.last_request: AnalysisRequest | None = None

    def analyze(self, request: AnalysisRequest) -> Any:
        self.calls += 1
        self.last_request = request
        if self._error is not None:
            raise self._error
        assert self._report is not None
        return self._report

    def analyze_recommendation(self, request: AnalysisRequest) -> Recommendation:
        self.calls += 1
        self.last_request = request
        if self._error is not None:
            raise self._error
        assert self._recommendation is not None
        return self._recommendation


def _recommendation(instrument: Instrument) -> Recommendation:
    return Recommendation(
        instrument=instrument,
        action=RecommendationAction.BUY,
        conviction=0.75,
        rationale="Platform test recommendation.",
        generated_at=FIXED_NOW,
    )


class TestPublicApi:
    def test_exports(self) -> None:
        assert DSPPlatform is not None
        assert AnalysisRequest is not None
        assert issubclass(PlatformError, Exception)

    def test_sprint_73_exports(self) -> None:
        from dsp_platform import (
            PlatformHealthService,
            assert_application_imports,
            load_platform_config,
        )

        assert PlatformHealthService is not None
        assert callable(load_platform_config)
        assert callable(assert_application_imports)


class TestDependencyInjection:
    def test_analyze_delegates_to_orchestrator(
        self, instrument: Instrument
    ) -> None:
        expected = _recommendation(instrument)
        fake = _FakeAnalysisService(expected)
        platform = DSPPlatform(analysis_service=fake)  # type: ignore[arg-type]

        request = AnalysisRequest(
            instrument=instrument,
            start=date(2024, 1, 1),
            end=date(2024, 6, 1),
        )
        result = platform.analyze(request)

        assert result is expected
        assert fake.calls == 1
        assert fake.last_request == request

    def test_make_request_applies_feature_defaults(
        self, instrument: Instrument
    ) -> None:
        fake = _FakeAnalysisService(_recommendation(instrument))
        platform = DSPPlatform(
            analysis_service=fake,  # type: ignore[arg-type]
            features=FeatureFlags(
                include_fundamentals=False,
                include_economic=False,
                include_valuation=False,
                allow_partial=False,
            ),
        )
        request = platform.make_request(
            instrument, date(2024, 1, 1), date(2024, 6, 1)
        )
        assert request.include_fundamentals is False
        assert request.include_economic is False
        assert request.include_valuation is False
        assert request.allow_partial is False

    def test_make_request_explicit_override(
        self, instrument: Instrument
    ) -> None:
        fake = _FakeAnalysisService(_recommendation(instrument))
        platform = DSPPlatform(
            analysis_service=fake,  # type: ignore[arg-type]
            features=FeatureFlags(include_economic=False),
        )
        request = platform.make_request(
            instrument,
            date(2024, 1, 1),
            date(2024, 6, 1),
            include_economic=True,
        )
        assert request.include_economic is True


class TestErrorTranslation:
    def test_orchestration_error_becomes_platform_error(
        self, instrument: Instrument
    ) -> None:
        fake = _FakeAnalysisService(
            error=OrchestrationError("technical analysis failed")
        )
        platform = DSPPlatform(analysis_service=fake)  # type: ignore[arg-type]
        with pytest.raises(PlatformError, match="platform analysis failed"):
            platform.analyze(
                AnalysisRequest(
                    instrument=instrument,
                    start=date(2024, 1, 1),
                    end=date(2024, 6, 1),
                )
            )

    def test_does_not_leak_orchestration_type(
        self, instrument: Instrument
    ) -> None:
        fake = _FakeAnalysisService(error=OrchestrationError("boom"))
        platform = DSPPlatform(analysis_service=fake)  # type: ignore[arg-type]
        with pytest.raises(PlatformError) as exc_info:
            platform.analyze(
                AnalysisRequest(
                    instrument=instrument,
                    start=date(2024, 1, 1),
                    end=date(2024, 6, 1),
                )
            )
        assert not isinstance(exc_info.value, OrchestrationError)

    def test_deterministic(self, instrument: Instrument) -> None:
        expected = _recommendation(instrument)
        fake = _FakeAnalysisService(expected)
        platform = DSPPlatform(analysis_service=fake)  # type: ignore[arg-type]
        request = AnalysisRequest(
            instrument=instrument,
            start=date(2024, 1, 1),
            end=date(2024, 6, 1),
        )
        assert platform.analyze(request) == platform.analyze(request)


class TestDecisionPackApi:
    def test_analyze_decision_pack_returns_pack(
        self, instrument: Instrument
    ) -> None:
        from ai_committee import (
            CommitteeReport,
            Decision,
            InvestmentDecision,
            MemberVote,
            Opinion,
        )
        from contracts.domain.evidence import Evidence
        from contracts.enums import EngineSource
        from dsp_platform import DecisionPack

        op = Opinion(
            source="technical",
            recommendation=Decision.BUY,
            reasoning="Trend support.",
            evidence=(
                Evidence(
                    source_engine=EngineSource.INDICATOR_ENGINE,
                    claim="trend up",
                    value=1.0,
                    reference="test",
                    weight=0.8,
                ),
            ),
            engine=EngineSource.AI_COMMITTEE,
        )
        report = CommitteeReport(
            instrument=instrument,
            opinions=(op,),
            votes=(
                MemberVote(
                    source="technical",
                    recommendation=Decision.BUY,
                    opinion=op,
                ),
            ),
            decision=InvestmentDecision(
                instrument=instrument,
                decision=Decision.BUY,
                rationale="Buy.",
                decided_at=FIXED_NOW,
            ),
            voting_summary="1/1 buy",
            explanation="Aligned.",
        )
        fake = _FakeAnalysisService(report=report)
        platform = DSPPlatform(analysis_service=fake)  # type: ignore[arg-type]
        pack = platform.analyze_decision_pack(
            AnalysisRequest(
                instrument=instrument,
                start=date(2024, 1, 1),
                end=date(2024, 6, 1),
            )
        )
        assert isinstance(pack, DecisionPack)
        assert pack.recommendation.instrument == instrument
        assert pack.brief.action is pack.recommendation.action
        assert pack.assurance.action is pack.recommendation.action

    def test_analyze_still_returns_recommendation(
        self, instrument: Instrument
    ) -> None:
        expected = _recommendation(instrument)
        fake = _FakeAnalysisService(expected)
        platform = DSPPlatform(analysis_service=fake)  # type: ignore[arg-type]
        result = platform.analyze(
            AnalysisRequest(
                instrument=instrument,
                start=date(2024, 1, 1),
                end=date(2024, 6, 1),
            )
        )
        assert result is expected


class TestUniverseApi:
    def test_analyze_universe_uses_decision_packs(
        self, instrument: Instrument
    ) -> None:
        from ai_committee import (
            CommitteeReport,
            Decision,
            InvestmentDecision,
            MemberVote,
            Opinion,
        )
        from contracts.domain.evidence import Evidence
        from contracts.enums import AssetClass, EngineSource
        from dsp_platform import (
            BatchStatus,
            InvestmentUniverse,
            MultiStockAnalysisRequest,
        )

        class _PerInstrumentFake:
            def __init__(self) -> None:
                self.analyze_calls = 0

            def analyze(self, request: AnalysisRequest) -> Any:
                self.analyze_calls += 1
                inst = request.instrument
                op = Opinion(
                    source="technical",
                    recommendation=Decision.BUY,
                    reasoning="ok",
                    evidence=(
                        Evidence(
                            source_engine=EngineSource.INDICATOR_ENGINE,
                            claim="up",
                            value=1.0,
                            reference="t",
                            weight=0.5,
                        ),
                    ),
                    engine=EngineSource.AI_COMMITTEE,
                )
                return CommitteeReport(
                    instrument=inst,
                    opinions=(op,),
                    votes=(
                        MemberVote(
                            source="technical",
                            recommendation=Decision.BUY,
                            opinion=op,
                        ),
                    ),
                    decision=InvestmentDecision(
                        instrument=inst,
                        decision=Decision.BUY,
                        rationale="Buy.",
                        decided_at=FIXED_NOW,
                    ),
                    voting_summary="1/1",
                    explanation="ok",
                )

            def analyze_recommendation(
                self, request: AnalysisRequest
            ) -> Recommendation:
                raise AssertionError("should not use analyze_recommendation")

        other = Instrument(
            symbol="MSFT", asset_class=AssetClass.EQUITY, currency="USD"
        )
        universe = InvestmentUniverse(name="tech")
        universe.add(instrument)
        universe.add(other)
        fake = _PerInstrumentFake()
        platform = DSPPlatform(analysis_service=fake)  # type: ignore[arg-type]
        result = platform.analyze_universe(
            MultiStockAnalysisRequest(
                universe=universe,
                start=date(2024, 1, 1),
                end=date(2024, 6, 1),
            )
        )
        assert result.status is BatchStatus.SUCCESS
        assert len(result.packs) == 2
        assert fake.analyze_calls == 2
        assert {p.recommendation.instrument.symbol for p in result.packs} == {
            "AAPL",
            "MSFT",
        }


class TestFromConfig:
    def test_requires_fred_key_outside_test(self) -> None:
        config = PlatformConfig(
            environment=Environment.PRODUCTION,
            providers=ProviderSettings(enable_economic=True),
            secrets=PlatformSecrets(fred_api_key=None),
        )
        with pytest.raises(PlatformError, match="fred_api_key"):
            DSPPlatform.from_config(config)

    def test_builds_in_test_without_fred_key(self) -> None:
        config = PlatformConfig(
            environment=Environment.TEST,
            providers=ProviderSettings(
                enable_market=True,
                enable_fundamentals=True,
                enable_economic=True,
            ),
            secrets=PlatformSecrets(fred_api_key=None),
        )
        platform = DSPPlatform.from_config(config)
        assert isinstance(platform, DSPPlatform)
        assert platform.features.allow_partial is True
