"""Tests for FRED registration and EconomicDataService wiring."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from contracts.domain.economic_series import EconomicSeries
from data_engine.adapters.fred import (
    FRED_METADATA,
    FredEconomicAdapter,
    build_fred_adapter,
    register_fred,
    supported_indicator_codes,
)
from data_engine.cache import InMemoryCache
from data_engine.models import EconomicRequest
from data_engine.providers import DataCapability, ProviderFactory, ProviderRegistry
from data_engine.services import EconomicDataService


class _FakeHttpClient:
    def get_json(
        self, url: str, *, params: Mapping[str, str] | None = None
    ) -> Mapping[str, Any]:
        return {
            "observations": [
                {"date": "2023-01-01", "value": "100.0"},
                {"date": "2023-02-01", "value": "101.0"},
            ]
        }


class TestBuildAndRegister:
    def test_builds_adapter(self) -> None:
        adapter = build_fred_adapter({"api_key": "x"})
        assert isinstance(adapter, FredEconomicAdapter)
        assert adapter.provider_name == "fred"

    def test_registers_with_economic_capability(self) -> None:
        factory = ProviderFactory()
        registry = ProviderRegistry()
        adapter = register_fred(factory, registry, {"api_key": "x"})
        assert factory.is_registered("fred")
        assert registry.get("fred") is adapter
        assert registry.get_metadata("fred") == FRED_METADATA
        assert registry.filter_by_capability(DataCapability.ECONOMIC_DATA) == ("fred",)

    def test_supported_codes_include_core_set(self) -> None:
        codes = supported_indicator_codes()
        assert "GDP" in codes
        assert "CPI" in codes
        assert "PMI" in codes
        assert "M2" in codes


class TestEconomicServiceThroughRegistry:
    @pytest.fixture
    def registry(self) -> ProviderRegistry:
        registry = ProviderRegistry()
        adapter = FredEconomicAdapter(http_client=_FakeHttpClient())
        registry.register(adapter, FRED_METADATA)
        return registry

    def test_service_retrieves_and_caches(
        self, registry: ProviderRegistry
    ) -> None:
        service = EconomicDataService(
            providers=registry, cache=InMemoryCache(), default_provider="fred"
        )
        request = EconomicRequest(indicator_code="GDP", country="US", limit=1)
        first = service.get_economic_series(request)
        second = service.get_economic_series(request)
        assert isinstance(first, EconomicSeries)
        assert len(first.points) == 1
        assert first == second

    def test_get_available_series_skips_failures(
        self, registry: ProviderRegistry
    ) -> None:
        service = EconomicDataService(
            providers=registry, cache=InMemoryCache(), default_provider="fred"
        )
        available = service.get_available_series(
            indicator_codes=("GDP", "VIX", "CPI"), country="US"
        )
        assert set(available) == {"GDP", "CPI"}
        assert "VIX" not in available
