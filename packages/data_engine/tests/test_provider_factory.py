"""Tests for data_engine.providers.factory."""

from typing import Any

import pytest

from data_engine.adapters import BaseAdapter
from data_engine.providers import ProviderFactory


class FakeAdapter(BaseAdapter):
    """Minimal in-test fake adapter used only to exercise the factory."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    @property
    def provider_name(self) -> str:
        return "fake_vendor"


def _build_fake_adapter(config: dict[str, Any]) -> FakeAdapter:
    return FakeAdapter(api_key=config["api_key"])


class TestProviderFactory:
    """Tests for the ProviderFactory."""

    def test_is_registered_is_false_for_unknown_provider(self) -> None:
        factory = ProviderFactory()
        assert factory.is_registered("fake_vendor") is False

    def test_register_builder_then_create_builds_adapter(self) -> None:
        factory = ProviderFactory()
        factory.register_builder("fake_vendor", _build_fake_adapter)

        adapter = factory.create("fake_vendor", {"api_key": "secret"})

        assert isinstance(adapter, FakeAdapter)
        assert adapter.api_key == "secret"
        assert factory.is_registered("fake_vendor") is True

    def test_create_without_config_passes_empty_mapping(self) -> None:
        factory = ProviderFactory()
        received: dict[str, Any] = {}

        def builder(config: dict[str, Any]) -> FakeAdapter:
            received.update(config)
            return FakeAdapter(api_key="none")

        factory.register_builder("fake_vendor", builder)
        factory.create("fake_vendor")

        assert received == {}

    def test_create_unregistered_provider_raises_key_error(self) -> None:
        factory = ProviderFactory()
        with pytest.raises(KeyError):
            factory.create("unknown")

    def test_registering_conflicting_builder_raises(self) -> None:
        factory = ProviderFactory()
        factory.register_builder("fake_vendor", _build_fake_adapter)

        def other_builder(config: dict[str, Any]) -> FakeAdapter:
            return FakeAdapter(api_key=config["api_key"])

        with pytest.raises(ValueError, match="already registered"):
            factory.register_builder("fake_vendor", other_builder)
