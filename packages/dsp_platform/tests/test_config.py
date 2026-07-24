"""Tests for PlatformConfig validation."""

from __future__ import annotations

import pytest

from dsp_platform import (
    CacheSettings,
    Environment,
    FeatureFlags,
    PlatformConfig,
    PlatformError,
    PlatformSecrets,
    ProviderSettings,
    TimeoutSettings,
)


class TestConfig:
    def test_defaults(self) -> None:
        config = PlatformConfig()
        assert config.environment is Environment.DEVELOPMENT
        assert config.providers.market_provider_id == "yahoo_finance"
        assert config.features.allow_partial is True

    def test_secrets_repr_redacts(self) -> None:
        secrets = PlatformSecrets(fred_api_key="super-secret")
        text = repr(secrets)
        assert "super-secret" not in text
        assert "set" in text

    def test_empty_provider_id_raises(self) -> None:
        with pytest.raises(PlatformError, match="market_provider_id"):
            ProviderSettings(market_provider_id="  ")

    def test_negative_cache_ttl_raises(self) -> None:
        with pytest.raises(PlatformError, match="ttl_seconds"):
            CacheSettings(ttl_seconds=-1)

    def test_non_positive_timeout_raises(self) -> None:
        with pytest.raises(PlatformError, match="request_seconds"):
            TimeoutSettings(request_seconds=0)

    def test_immutable_config(self) -> None:
        config = PlatformConfig(features=FeatureFlags(include_economic=False))
        with pytest.raises(AttributeError):
            config.environment = Environment.PRODUCTION  # type: ignore[misc]
