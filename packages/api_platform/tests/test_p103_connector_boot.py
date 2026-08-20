"""P1-03 — investment fail-closed at connector use; auth boot stays independent.

Historical note: an earlier revision refused ``create_app`` when production
investment connectors were unavailable. That coupled client authentication to
Upstox/FMP boot. Validation now lives in adapter factories / investment paths.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from data_engine.exceptions import ConnectorConfigurationError
from data_engine.market_quote.adapters import build_default_quote_adapter_from_env
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration


@pytest.fixture()
def platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )


def _clear_investment_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_JWT_SECRET", "unit-test-production-secret-not-default")
    # Isolate investment-decoupling from Postgres/region runtime gates.
    monkeypatch.setenv("DSP_INFRA_OFFLINE", "1")
    monkeypatch.setattr(
        "api_platform.api.durable_product_stores.require_durable_product_database",
        lambda database: None,
    )
    for key in (
        "DSP_INVESTMENT_DATA_PROVIDER",
        "DSP_UPSTOX_ANALYTICS_TOKEN",
        "DSP_UPSTOX_ACCESS_TOKEN",
        "DSP_FMP_API_KEY",
        "DSP_INVESTMENT_FMP_API_KEY",
        "DSP_MARKET_QUOTE_API_KEY",
        "DSP_MARKET_QUOTE_BASE_URL",
        "DSP_MARKET_QUOTE_MEMORY",
        "DSP_FINANCIAL_STATEMENT_API_KEY",
        "DSP_FINANCIAL_STATEMENT_BASE_URL",
        "DSP_FINANCIAL_STATEMENT_MEMORY",
    ):
        monkeypatch.delenv(key, raising=False)


def test_create_app_production_boots_without_investment_connectors(
    monkeypatch: pytest.MonkeyPatch, platform: DSPPlatform
) -> None:
    """Auth/core API may start even when investment credentials are absent."""
    from api_platform import create_app

    _clear_investment_env(monkeypatch)
    app = create_app(platform=platform, enable_security=False)
    assert app is not None
    client = TestClient(app)
    assert client.get("/api/v1/auth/session").status_code == 200


def test_production_investment_factory_still_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P1-03 still refuses Null/memory selection when building connectors."""
    _clear_investment_env(monkeypatch)
    with pytest.raises(ConnectorConfigurationError, match="P1-03"):
        build_default_quote_adapter_from_env()


def test_create_app_non_production_still_allows_null_default(
    platform: DSPPlatform,
) -> None:
    from api_platform import create_app

    app = create_app(platform=platform, enable_security=False)
    assert app is not None
