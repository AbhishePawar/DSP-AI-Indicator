"""Application-layer services for the Data Engine.

A service composes ports, the provider registry, and the cache to fulfill
a request, without knowing which concrete provider or cache backend is in
use. This is the Data Engine's own internal application layer — distinct
from the platform-wide ``orchestration`` package (not yet built), which
will compose whole engines together rather than composing within one.
"""

from __future__ import annotations

from contracts.domain.economic_series import EconomicSeries
from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.price_series import PriceSeries
from data_engine.builders import EconomicSeriesBuilder, FundamentalStatementsBuilder
from data_engine.cache import CachePort
from data_engine.exceptions import DataEngineError, InvalidProviderDataError
from data_engine.models import EconomicRequest, FundamentalsRequest, PriceSeriesRequest
from data_engine.ports import EconomicDataPort, FundamentalsDataPort, MarketDataPort
from data_engine.providers import ProviderRegistry

__all__ = ["EconomicDataService", "FundamentalsDataService", "MarketDataService"]



class MarketDataService:
    """Coordinates cache and provider lookups to satisfy price-series requests.

    Lookup order: check the cache first; on a miss, delegate to the named
    (or configured default) provider through its ``MarketDataPort``
    interface, then populate the cache before returning. No provider- or
    market-specific logic lives here — only this generic coordination.
    """

    def __init__(
        self,
        *,
        providers: ProviderRegistry,
        cache: CachePort[str, PriceSeries],
        default_provider: str | None = None,
        cache_ttl_seconds: float | None = None,
    ) -> None:
        """Initialize the service with its collaborators.

        Args:
            providers: Registry of available ``MarketDataPort`` providers.
            cache: Cache used to avoid redundant provider calls.
            default_provider: Provider name to use when a request does
                not specify one explicitly.
            cache_ttl_seconds: Default cache time-to-live applied to
                newly cached price series.
        """
        self._providers = providers
        self._cache = cache
        self._default_provider = default_provider
        self._cache_ttl_seconds = cache_ttl_seconds

    def get_price_series(self, request: PriceSeriesRequest) -> PriceSeries:
        """Fulfill a price-series request via cache-then-provider lookup.

        Args:
            request: The price series request to fulfill.

        Returns:
            The requested price series, from cache if available.

        Raises:
            DataEngineError: If no provider name is available (neither
                the request nor the service has one configured), or the
                resolved provider does not support market data.
            KeyError: If the resolved provider name is not registered.
        """
        provider_name = request.provider_name or self._default_provider
        if provider_name is None:
            msg = "No provider_name given and no default_provider configured"
            raise DataEngineError(msg)

        cache_key = self._cache_key(request, provider_name)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        adapter = self._providers.get(provider_name)
        if not isinstance(adapter, MarketDataPort):
            msg = f"Provider '{provider_name}' does not support market data"
            raise DataEngineError(msg)

        series = adapter.get_price_series(
            request.instrument, request.frequency, request.start, request.end
        )
        self._cache.set(cache_key, series, ttl_seconds=self._cache_ttl_seconds)
        return series

    @staticmethod
    def _cache_key(request: PriceSeriesRequest, provider_name: str) -> str:
        """Build a deterministic cache key for a price-series request."""
        return (
            f"{provider_name}:{request.instrument.symbol}:{request.frequency}:"
            f"{request.start.isoformat()}:{request.end.isoformat()}"
        )


class FundamentalsDataService:
    """Coordinates cache and provider lookups for fundamental statements.

    Lookup order mirrors :class:`MarketDataService`: cache first, then
    the named (or default) ``FundamentalsDataPort``, then cache populate.
    The returned tuple is always run through
    :class:`~data_engine.builders.FundamentalStatementsBuilder` so
    callers receive a canonical, most-recent-first bundle ready for
    Sprint 6.4 ``FinancialSnapshot`` construction.
    """

    def __init__(
        self,
        *,
        providers: ProviderRegistry,
        cache: CachePort[str, tuple[FundamentalStatement, ...]],
        default_provider: str | None = None,
        cache_ttl_seconds: float | None = None,
    ) -> None:
        """Initialize the service with its collaborators.

        Args:
            providers: Registry of available fundamentals providers.
            cache: Cache used to avoid redundant provider calls.
            default_provider: Provider name to use when a request does
                not specify one explicitly.
            cache_ttl_seconds: Default cache time-to-live applied to
                newly cached statement tuples.
        """
        self._providers = providers
        self._cache = cache
        self._default_provider = default_provider
        self._cache_ttl_seconds = cache_ttl_seconds

    def get_fundamental_statements(
        self, request: FundamentalsRequest
    ) -> tuple[FundamentalStatement, ...]:
        """Fulfill a fundamentals request via cache-then-provider lookup.

        Args:
            request: The fundamentals request to fulfill.

        Returns:
            Validated statements ordered most-recent-first.

        Raises:
            DataEngineError: If no provider name is available, or the
                resolved provider does not implement
                ``FundamentalsDataPort``.
            KeyError: If the resolved provider name is not registered.
        """
        provider_name = request.provider_name or self._default_provider
        if provider_name is None:
            msg = "No provider_name given and no default_provider configured"
            raise DataEngineError(msg)

        cache_key = self._cache_key(request, provider_name)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        adapter = self._providers.get(provider_name)
        if not isinstance(adapter, FundamentalsDataPort):
            msg = f"Provider '{provider_name}' does not support fundamentals"
            raise DataEngineError(msg)

        statements = adapter.get_fundamental_statements(
            request.instrument, request.period_type, limit=request.limit
        )
        assembled = FundamentalStatementsBuilder.build(
            request.instrument, statements
        )
        self._cache.set(cache_key, assembled, ttl_seconds=self._cache_ttl_seconds)
        return assembled

    @staticmethod
    def _cache_key(request: FundamentalsRequest, provider_name: str) -> str:
        """Build a deterministic cache key for a fundamentals request."""
        limit_token = "all" if request.limit is None else str(request.limit)
        return (
            f"{provider_name}:{request.instrument.symbol}:"
            f"{request.period_type.value}:{limit_token}"
        )


class EconomicDataService:
    """Coordinates cache and provider lookups for macroeconomic series.

    Lookup order mirrors the other Data Engine services. Successful
    results are run through :class:`EconomicSeriesBuilder`. For batch
    acquisition, :meth:`get_available_series` collects multiple codes
    and skips unavailable ones without aborting the whole request —
    supporting Sprint 6.4 snapshot assembly when some indicators are
    missing.
    """

    def __init__(
        self,
        *,
        providers: ProviderRegistry,
        cache: CachePort[str, EconomicSeries],
        default_provider: str | None = None,
        cache_ttl_seconds: float | None = None,
    ) -> None:
        """Initialize the service with its collaborators."""
        self._providers = providers
        self._cache = cache
        self._default_provider = default_provider
        self._cache_ttl_seconds = cache_ttl_seconds

    def get_economic_series(self, request: EconomicRequest) -> EconomicSeries:
        """Fulfill a single-series request via cache-then-provider lookup.

        Raises:
            DataEngineError: If no provider is configured or the resolved
                provider does not implement ``EconomicDataPort``.
            KeyError: If the provider name is not registered.
        """
        provider_name = request.provider_name or self._default_provider
        if provider_name is None:
            msg = "No provider_name given and no default_provider configured"
            raise DataEngineError(msg)

        cache_key = self._cache_key(request, provider_name)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        adapter = self._providers.get(provider_name)
        if not isinstance(adapter, EconomicDataPort):
            msg = f"Provider '{provider_name}' does not support economic data"
            raise DataEngineError(msg)

        series = adapter.get_economic_series(
            request.indicator_code, request.country
        )
        assembled = EconomicSeriesBuilder.build(
            series,
            expected_country=request.country,
            limit=request.limit,
        )
        self._cache.set(cache_key, assembled, ttl_seconds=self._cache_ttl_seconds)
        return assembled

    def get_available_series(
        self,
        *,
        indicator_codes: tuple[str, ...] | list[str],
        country: str,
        provider_name: str | None = None,
        limit: int | None = None,
    ) -> dict[str, EconomicSeries]:
        """Fetch multiple series, skipping failures without aborting.

        Args:
            indicator_codes: Platform indicator codes to request.
            country: ISO country code shared by all requests.
            provider_name: Optional explicit provider override.
            limit: Optional per-series observation limit.

        Returns:
            Mapping of canonical ``indicator_code`` → ``EconomicSeries``
            for every series that resolved successfully. Unsupported or
            empty series are omitted rather than raising.
        """
        available: dict[str, EconomicSeries] = {}
        for code in indicator_codes:
            request = EconomicRequest(
                indicator_code=code,
                country=country,
                limit=limit,
                provider_name=provider_name,
            )
            try:
                series = self.get_economic_series(request)
            except (DataEngineError, InvalidProviderDataError, KeyError):
                continue
            available[series.indicator_code] = series
        return available

    @staticmethod
    def _cache_key(request: EconomicRequest, provider_name: str) -> str:
        """Build a deterministic cache key for an economic series request."""
        limit_token = "all" if request.limit is None else str(request.limit)
        return (
            f"{provider_name}:{request.indicator_code.strip().upper()}:"
            f"{request.country.strip().upper()}:{limit_token}"
        )
