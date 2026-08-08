# EPIC-D001 — Market Data Provider Architecture

## Port

`MarketQuotePort` (`data_engine.market_quote.service`):

- `get_quote(instrument) -> AuthenticatedMarketQuote | None`
- `health() -> QuoteProviderHealth`
- `provider_id: str`

Adapters must **never invent** symbols or numbers. Missing → `None`. Invalid → raise / reject via `validate_authenticated_quote`.

## Registry

`MarketQuoteProviderRegistry` registers named adapters and an optional default.

## Service (resilience)

`MarketQuoteService` wraps a port with:

1. **Rate limiting** — `RateLimiter`
2. **Retry + timeout** — `RetryPolicy` (bounded attempts/backoff)
3. **Circuit breaker** — `CircuitBreaker` / `CircuitOpenError`
4. **Caching** — `CachePort` (default `InMemoryCache`) with TTL; cache hits mark provenance
5. **Validation** — reject dummy/placeholder source types; inconsistent available/null
6. **Provenance & timestamping** — `MarketQuoteProvenance`
7. **Metrics & structured logging** — `MarketQuoteServiceMetrics` + logger `data_engine.market_quote`
8. **Health** — `service.health().to_dict()`

## Adapters

| Adapter | Auth | Behaviour |
|---|---|---|
| `NullAuthenticatedQuoteAdapter` | none | Always unavailable (safe default) |
| `InMemoryAuthenticatedQuoteAdapter` | `api_key` required | Seeded quotes only |
| `ConfiguredHttpQuoteAdapter` | API key + base URL | Licensed vendor HTTP JSON |

Selection: `build_default_quote_adapter_from_env()`.

## Public surfaces

- Python: `DSPPlatform.get_authenticated_market_quote` / `market_quote_health`
- HTTP: `GET /api/v1/market/quote`, `GET /api/v1/market/health`
- Web: `api.marketQuote(symbol)` → institutional dashboard mapper

## Forbidden

- Unauthenticated free scrapes presented as verified market data
- Fabricating OHLC / market cap when provider returns gaps
- Changing `/analyse` contract or engine scoring
