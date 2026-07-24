"""Composition-root wiring for DSPPlatform.from_config.

This module is the only place in ``dsp_platform`` that may import Data
Engine adapters / registries. ``DSPPlatform.analyze`` never calls
providers, engines, or the committee directly — it always goes through
``InvestmentAnalysisService``.
"""

from __future__ import annotations

from data_engine import (
    EconomicDataService,
    FundamentalsDataService,
    InMemoryCache,
    MarketDataService,
    ProviderFactory,
    ProviderRegistry,
    register_fred,
    register_yahoo_finance,
    register_yahoo_finance_fundamentals,
)
from dsp_platform.config import Environment, PlatformConfig
from dsp_platform.exceptions import PlatformError
from orchestration import InvestmentAnalysisService
from snapshot_bridge import EconomicBridgeService, FinancialBridgeService

__all__ = ["build_analysis_service"]


def build_analysis_service(config: PlatformConfig) -> InvestmentAnalysisService:
    """Build an ``InvestmentAnalysisService`` from immutable config.

    Registers enabled providers, constructs Data Engine services and
    snapshot bridges, and returns the orchestrator. Raises
    ``PlatformError`` if economic data is enabled without a FRED API key
    in non-test environments (live HTTP would otherwise fail opaquely).
    """
    try:
        factory = ProviderFactory()
        registry = ProviderRegistry()
        timeout = config.timeouts.request_seconds

        if config.providers.enable_market:
            register_yahoo_finance(
                factory, registry, {"timeout_seconds": timeout}
            )
        if config.providers.enable_fundamentals:
            register_yahoo_finance_fundamentals(
                factory, registry, {"timeout_seconds": timeout}
            )
        if config.providers.enable_economic:
            # Allow missing key only in TEST (unit tests inject fakes).
            # DEVELOPMENT/PRODUCTION require an injected key for live FRED.
            if (
                config.secrets.fred_api_key is None
                and config.environment is not Environment.TEST
            ):
                msg = (
                    "fred_api_key is required when enable_economic is "
                    "True outside Environment.TEST"
                )
                raise PlatformError(msg)
            register_fred(
                factory,
                registry,
                {
                    "timeout_seconds": timeout,
                    "api_key": config.secrets.fred_api_key,
                },
            )

        cache_ttl = config.cache.ttl_seconds
        market = MarketDataService(
            providers=registry,
            cache=InMemoryCache(),
            default_provider=(
                config.providers.market_provider_id
                if config.providers.enable_market
                else None
            ),
            cache_ttl_seconds=cache_ttl,
        )
        fundamentals = FundamentalsDataService(
            providers=registry,
            cache=InMemoryCache(),
            default_provider=(
                config.providers.fundamentals_provider_id
                if config.providers.enable_fundamentals
                else None
            ),
            cache_ttl_seconds=cache_ttl,
        )
        economic = EconomicDataService(
            providers=registry,
            cache=InMemoryCache(),
            default_provider=(
                config.providers.economic_provider_id
                if config.providers.enable_economic
                else None
            ),
            cache_ttl_seconds=cache_ttl,
        )

        return InvestmentAnalysisService(
            market_data=market,
            financial_bridge=FinancialBridgeService(fundamentals=fundamentals),
            economic_bridge=EconomicBridgeService(economic=economic),
        )
    except PlatformError:
        raise
    except Exception as exc:
        msg = f"failed to build platform analysis service: {exc}"
        raise PlatformError(msg) from exc
