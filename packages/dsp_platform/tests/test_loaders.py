"""Tests for optional environment configuration loaders."""

from __future__ import annotations

import pytest

from dsp_platform import (
    Environment,
    PlatformError,
    PlatformSecrets,
    load_platform_config,
    load_secrets_from_environ,
)


class TestLoaders:
    def test_defaults_when_empty(self) -> None:
        config = load_platform_config({})
        assert config.environment is Environment.DEVELOPMENT
        assert config.providers.enable_market is True
        assert config.secrets.fred_api_key is None

    def test_loads_environment_and_secrets(self) -> None:
        config = load_platform_config(
            {
                "DSP_AI_ENVIRONMENT": "production",
                "DSP_AI_FRED_API_KEY": "secret-key",
                "DSP_AI_ENABLE_ECONOMIC": "false",
                "DSP_AI_CACHE_TTL_SECONDS": "60",
                "DSP_AI_REQUEST_TIMEOUT_SECONDS": "5",
                "DSP_AI_ALLOW_PARTIAL": "0",
            }
        )
        assert config.environment is Environment.PRODUCTION
        assert config.secrets.fred_api_key == "secret-key"
        assert config.providers.enable_economic is False
        assert config.cache.ttl_seconds == 60.0
        assert config.timeouts.request_seconds == 5.0
        assert config.features.allow_partial is False

    def test_loads_include_valuation(self) -> None:
        config = load_platform_config({"DSP_AI_INCLUDE_VALUATION": "false"})
        assert config.features.include_valuation is False

    def test_explicit_secrets_override_environ(self) -> None:
        config = load_platform_config(
            {"DSP_AI_FRED_API_KEY": "from-env"},
            secrets=PlatformSecrets(fred_api_key="injected"),
        )
        assert config.secrets.fred_api_key == "injected"

    def test_invalid_environment_raises(self) -> None:
        with pytest.raises(PlatformError, match="DSP_AI_ENVIRONMENT"):
            load_platform_config({"DSP_AI_ENVIRONMENT": "staging"})

    def test_invalid_bool_raises(self) -> None:
        with pytest.raises(PlatformError, match="boolean"):
            load_platform_config({"DSP_AI_ENABLE_MARKET": "maybe"})

    def test_secrets_loader_strips_blank(self) -> None:
        secrets = load_secrets_from_environ({"DSP_AI_FRED_API_KEY": "  "})
        assert secrets.fred_api_key is None

    def test_null_cache_ttl(self) -> None:
        config = load_platform_config({"DSP_AI_CACHE_TTL_SECONDS": "none"})
        assert config.cache.ttl_seconds is None

    def test_no_hardcoded_secrets_in_defaults(self) -> None:
        config = load_platform_config({})
        assert "key" not in repr(config.secrets).lower() or "unset" in repr(
            config.secrets
        )
        assert config.secrets.fred_api_key is None
