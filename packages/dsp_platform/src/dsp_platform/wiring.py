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
)
from data_engine.providers import (
    AuthenticationType,
    ProviderCapabilities,
    ProviderMetadata,
    RateLimitPolicy,
)

from dsp_platform.world_bank_adapter import (
    WorldBankEconomicAdapter,
)
from dsp_platform.research_retrieval.world_bank_data import (
    WorldBankDataService,
)
from dsp_platform.research_retrieval.url_safety import (
    DefaultSafeHttpFetcher,
    UrlSafetyPolicy,
)

from dsp_platform.config import Environment, PlatformConfig
from dsp_platform.exceptions import PlatformError
from orchestration import InvestmentAnalysisService
from snapshot_bridge import EconomicBridgeService, FinancialBridgeService

__all__ = ["build_analysis_service", "build_analysis_components"]


def build_analysis_service(config: PlatformConfig) -> InvestmentAnalysisService:
    """Compatibility wrapper returning only the analysis service."""
    service, _registry = build_analysis_components(config)
    return service


def build_analysis_components(
    config: PlatformConfig,
) -> tuple[InvestmentAnalysisService, ProviderRegistry]:
    """Build the analysis service and expose its provider registry.

    Registers enabled providers, constructs Data Engine services and
    snapshot bridges, and returns both the orchestrator and registry.
    Raises PlatformError if economic data is enabled without a FRED API
    key in non-test environments.
    """
    try:
        factory = ProviderFactory()
        registry = ProviderRegistry()
        timeout = config.timeouts.request_seconds

        if config.providers.enable_market or config.providers.enable_fundamentals:
            raise PlatformError(
                "Automatic commercial market/fundamentals providers are disabled. "
                "Use the verified-source composition API or inject a data service."
            )
        if config.providers.enable_economic:
            provider_id = config.providers.economic_provider_id

            if provider_id == "world_bank":

                adapter = WorldBankEconomicAdapter(
                    service=WorldBankDataService(
                        fetcher=DefaultSafeHttpFetcher(
                            policy=UrlSafetyPolicy(
                                timeout_seconds=timeout,
                                max_redirects=0,
                                max_body_bytes=2_000_000,
                            )
                        )
                    )
                )

                registry.register(
                    adapter,
                    ProviderMetadata(
                        provider_id="world_bank",
                        name="World Bank",
                        version="1.0.0",
                        description="Public annual Indian economic indicators",
                        homepage="https://data.worldbank.org",
                        capabilities=ProviderCapabilities.from_flags(
                            economic_data=True
                        ),
                        rate_limit=RateLimitPolicy(),
                        auth_type=AuthenticationType.NONE,
                        priority=1,
                    ),
                )

            elif provider_id == "fred":

                if (
                    config.secrets.fred_api_key is None
                    and config.environment is not Environment.TEST
                ):
                    raise PlatformError(
                        "fred_api_key is required when enable_economic is "
                        "True outside Environment.TEST"
                    )

                register_fred(
                    factory,
                    registry,
                    {
                        "timeout_seconds": timeout,
                        "api_key": config.secrets.fred_api_key,
                    },
                )

            else:

                raise PlatformError(
                    "Unsupported configured economic provider"
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

        service = InvestmentAnalysisService(
            market_data=market,
            financial_bridge=FinancialBridgeService(fundamentals=fundamentals),
            economic_bridge=EconomicBridgeService(economic=economic),
        )
        return service, registry
    except PlatformError:
        raise
    except Exception as exc:
        msg = f"failed to build platform analysis service: {exc}"
        raise PlatformError(msg) from exc
