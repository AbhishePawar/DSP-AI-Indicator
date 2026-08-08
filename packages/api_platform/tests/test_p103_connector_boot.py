"""P1-03 — production API boot refuses Null investment connectors."""

from __future__ import annotations

import pytest

from data_engine.exceptions import ConnectorConfigurationError
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration


@pytest.fixture()
def platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )


def test_create_app_production_rejects_null_connectors(
    monkeypatch: pytest.MonkeyPatch, platform: DSPPlatform
) -> None:
    from api_platform import create_app

    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_JWT_SECRET", "unit-test-production-secret-not-default")
    monkeypatch.delenv("DSP_MARKET_QUOTE_API_KEY", raising=False)
    monkeypatch.delenv("DSP_MARKET_QUOTE_BASE_URL", raising=False)
    monkeypatch.delenv("DSP_FINANCIAL_STATEMENT_API_KEY", raising=False)
    monkeypatch.delenv("DSP_FINANCIAL_STATEMENT_BASE_URL", raising=False)

    with pytest.raises(ConnectorConfigurationError, match="P1-03"):
        create_app(platform=platform, enable_security=False)


def test_create_app_non_production_still_allows_null_default(
    platform: DSPPlatform,
) -> None:
    from api_platform import create_app

    app = create_app(platform=platform, enable_security=False)
    assert app is not None
