"""K1.0 platform integration tests — orchestration only."""

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
    PlatformBuilder,
    PlatformConfiguration,
    PlatformConfigurationError,
    PlatformError,
    PlatformLifecycle,
    PlatformLifecycleError,
    PlatformMetadata,
    PlatformResult,
    PlatformStatus,
    ServiceRegistry,
    ServiceRegistryError,
    __version__,
)
from orchestration.models import AnalysisRequest as OrchRequest

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")


class _FakeAnalysisService:
    def __init__(self, recommendation: Recommendation) -> None:
        self._recommendation = recommendation
        self.calls = 0

    def analyze(self, request: AnalysisRequest) -> Any:
        self.calls += 1
        raise AssertionError("analyze should not be required for recommendation path")

    def analyze_recommendation(self, request: AnalysisRequest) -> Recommendation:
        self.calls += 1
        return self._recommendation


def _recommendation(instrument: Instrument) -> Recommendation:
    return Recommendation(
        instrument=instrument,
        action=RecommendationAction.BUY,
        conviction=0.75,
        rationale="K1.0 platform test.",
        generated_at=FIXED_NOW,
    )


class TestVersionAndExports:
    def test_platform_version(self) -> None:
        assert __version__ == "1.6.0"

    def test_k1_exports(self) -> None:
        assert PlatformBuilder is not None
        assert PlatformConfiguration is not None
        assert ServiceRegistry is not None
        assert PlatformLifecycle is not None
        assert PlatformMetadata is not None
        assert PlatformResult is not None


class TestServiceRegistry:
    def test_register_and_get(self) -> None:
        registry = ServiceRegistry()
        registry.register("alpha", object(), capability="analyze_company")
        assert registry.has("alpha")
        assert "analyze_company" in registry.list_capabilities()

    def test_duplicate_rejected(self) -> None:
        registry = ServiceRegistry()
        registry.register("alpha", object(), capability="x")
        with pytest.raises(ServiceRegistryError, match="duplicate"):
            registry.register("alpha", object(), capability="x")

    def test_unknown_service(self) -> None:
        registry = ServiceRegistry()
        with pytest.raises(ServiceRegistryError, match="unknown"):
            registry.get("missing")


class TestLifecycle:
    def test_ready_path(self) -> None:
        life = PlatformLifecycle()
        life.begin_initialize()
        life.mark_ready(note="boot")
        assert life.is_ready
        assert life.status is PlatformStatus.READY
        life.ensure_ready()

    def test_illegal_transition(self) -> None:
        life = PlatformLifecycle()
        with pytest.raises(PlatformLifecycleError, match="illegal"):
            life.mark_ready()


class TestConfiguration:
    def test_duplicate_capabilities_rejected(self) -> None:
        with pytest.raises(PlatformConfigurationError, match="duplicate"):
            PlatformConfiguration(
                enabled_capabilities=("analyze_company", "analyze_company")
            )

    def test_round_trip_legacy_config(self) -> None:
        from dsp_platform import PlatformConfig

        legacy = PlatformConfig(environment=Environment.TEST)
        cfg = PlatformConfiguration.from_platform_config(legacy)
        assert cfg.to_platform_config().environment is Environment.TEST


class TestPlatformBuilderAndInfo:
    def test_builder_requires_analysis_when_configured(
        self, instrument: Instrument
    ) -> None:
        with pytest.raises(PlatformConfigurationError, match="analysis_service"):
            PlatformBuilder().with_configuration(PlatformConfiguration()).build()

    def test_builder_ready_platform(self, instrument: Instrument) -> None:
        fake = _FakeAnalysisService(_recommendation(instrument))
        platform = (
            PlatformBuilder()
            .with_configuration(
                PlatformConfiguration(environment=Environment.TEST)
            )
            .with_analysis_service(fake)  # type: ignore[arg-type]
            .build()
        )
        info = platform.get_platform_info()
        assert isinstance(info, PlatformMetadata)
        assert info.version == "1.0.0"
        assert info.status is PlatformStatus.READY
        assert "analyze_company" in info.capabilities
        assert "analysis_service" in info.registered_services

    def test_analyze_company_envelope(self, instrument: Instrument) -> None:
        expected = _recommendation(instrument)
        fake = _FakeAnalysisService(expected)
        platform = DSPPlatform(analysis_service=fake)  # type: ignore[arg-type]
        request = AnalysisRequest(
            instrument=instrument,
            start=date(2024, 1, 1),
            end=date(2024, 6, 1),
        )
        # Decision-pack path needs full analyze(); use recommendation path.
        result = platform.analyze_company(request, as_decision_pack=False)
        assert result.ok is True
        assert result.capability == "analyze_company"
        assert result.payload == expected
        assert fake.calls == 1

    def test_export_report_immutable_envelope(self, instrument: Instrument) -> None:
        fake = _FakeAnalysisService(_recommendation(instrument))
        platform = DSPPlatform(analysis_service=fake)  # type: ignore[arg-type]
        report = {"id": "r1"}
        result = platform.export_report(report, format_name="json")
        assert result.ok is True
        assert result.payload["report"] is report
        assert "format=json" in result.limitations

    def test_health_check_envelope(self, instrument: Instrument) -> None:
        fake = _FakeAnalysisService(_recommendation(instrument))
        platform = (
            PlatformBuilder()
            .with_configuration(
                PlatformConfiguration(environment=Environment.TEST)
            )
            .with_analysis_service(fake)  # type: ignore[arg-type]
            .build()
        )
        result = platform.health_check()
        assert isinstance(result, PlatformResult)
        assert result.capability == "health_check"
        assert result.payload is not None

    def test_legacy_analyze_still_works(self, instrument: Instrument) -> None:
        expected = _recommendation(instrument)
        fake = _FakeAnalysisService(expected)
        platform = DSPPlatform(analysis_service=fake)  # type: ignore[arg-type]
        request = OrchRequest(
            instrument=instrument,
            start=date(2024, 1, 1),
            end=date(2024, 6, 1),
        )
        assert platform.analyze(request) == expected

    def test_disabled_capability(self, instrument: Instrument) -> None:
        fake = _FakeAnalysisService(_recommendation(instrument))
        platform = (
            PlatformBuilder()
            .with_configuration(
                PlatformConfiguration(
                    environment=Environment.TEST,
                    enabled_capabilities=("get_platform_info", "health_check"),
                )
            )
            .with_analysis_service(fake)  # type: ignore[arg-type]
            .build()
        )
        request = AnalysisRequest(
            instrument=instrument,
            start=date(2024, 1, 1),
            end=date(2024, 6, 1),
        )
        with pytest.raises(PlatformConfigurationError, match="disabled"):
            platform.analyze_company(request, as_decision_pack=False)


class TestFeatureFlagsPreserved:
    def test_make_request_defaults(self, instrument: Instrument) -> None:
        fake = _FakeAnalysisService(_recommendation(instrument))
        platform = DSPPlatform(
            analysis_service=fake,  # type: ignore[arg-type]
            features=FeatureFlags(include_valuation=False),
        )
        req = platform.make_request(
            instrument, date(2024, 1, 1), date(2024, 6, 1)
        )
        assert req.include_valuation is False
