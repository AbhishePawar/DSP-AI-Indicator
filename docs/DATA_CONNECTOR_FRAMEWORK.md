# Data Connector Framework — News, Filings, Ownership, Insider Trading, ESG, Transcripts

Status: **COMPLETE**
Priority: P0 · Core Infrastructure
Supports: **CV-001** · **CV-002** · RS compliance (thin client honesty)

## Goal

Fill the remaining "Data unavailable" gaps in the institutional company
workspace (Ownership, News, Documents/Filings, Insider Activity) with a
production-grade, multi-provider Data Connector Framework — **without**
adding scoring, aggregation, or business logic to API routers, and without
ever fabricating data when no provider is configured.

The framework generalizes the pattern already proven by EPIC-D001
(`market_quote`), EPIC-D002 (`financial_statement`), and EPIC-D003
(`corporate_actions`), and adds **automatic multi-provider failover** on
top of it via a new shared `connector_framework` package.

## Architecture

```
[Web thin client]
   GET /api/v1/{news|filings|ownership|insider-trading|esg|transcripts}
        ↓
[api_platform]  <domain>.router          (no data_engine import, no business logic)
        ↓
[dsp_platform]  DSPPlatform.get_authenticated_<domain>()
        ↓
[dsp_platform.<domain>]  façade: builds PriorityProviderRegistry from env,
                          wraps each provider in a resilient *Service,
                          orchestrates FailoverGroup across all of them
        ↓
[data_engine.<domain>]
   <Domain>ProviderPort → PriorityProviderRegistry → Adapter(s)
   <Domain>Service (cache, rate limit, retry, timeout, circuit breaker,
                    validation, provenance, metrics, logging, health)
        ↓
[data_engine.connector_framework]  shared building blocks reused by every
   domain: models (identity/provenance/health/field), registry, audit,
   HTTP client, FailoverGroup. Resilience primitives (RateLimiter,
   CircuitBreaker, RetryPolicy) are re-exported from market_quote.service
   rather than duplicated.
```

Each of the six domains follows the identical five-file layout:

```
data_engine/<domain>/
  models.py       Normalized domain models (embed ConnectorCompanyIdentity,
                   ConnectorProvenance, ConnectorField as needed)
  validation.py    Structural validation — rejects fabricated/out-of-range data
  service.py       <Domain>ProviderPort (interface) + <Domain>Service
                    (cache + rate limit + retry + circuit breaker wrapper)
  registry.py      <Domain>ProviderRegistry(PriorityProviderRegistry)
  adapters.py      Null / InMemory / vendor adapters + build_default_*_from_env
```

## Ports

| Port | Domain package | Query model | Bundle model |
|---|---|---|---|
| `NewsProviderPort` | `data_engine.news` | `NewsQuery` | `AuthenticatedNewsFeed` |
| `FilingsProviderPort` | `data_engine.filings` | `FilingsQuery` | `AuthenticatedFilings` |
| `OwnershipProviderPort` | `data_engine.ownership` | `OwnershipQuery` | `AuthenticatedOwnership` |
| `InsiderTradingProviderPort` | `data_engine.insider_trading` | `InsiderTradingQuery` | `AuthenticatedInsiderActivity` |
| `EsgProviderPort` | `data_engine.esg` | `EsgQuery` | `AuthenticatedEsgScore` |
| `TranscriptProviderPort` | `data_engine.transcripts` | `TranscriptQuery` | `AuthenticatedTranscripts` |

Every port is a `Protocol` with `get_<domain>(query) -> Bundle | None` plus
`health() -> ProviderHealth`. Adapters never leak vendor-specific field
names outside of `adapters.py` — everything is mapped into the shared
normalized models before it reaches the service layer.

## Shared connector framework (`data_engine.connector_framework`)

| Component | Purpose |
|---|---|
| `ConnectorCompanyIdentity`, `ConnectorProvenance`, `ProviderHealth`, `ConnectorField` | Shared envelope dataclasses every domain embeds instead of redefining |
| `PriorityProviderRegistry` | Generic priority-ordered, enable/disable-aware provider registry |
| `FailoverGroup` | Orchestrates an ordered sequence of resilient `*Service` instances; tries each in priority order, records attempted provider IDs, audits every attempt |
| `ProviderAuditPort` (+ `LoggingProviderAuditPort`, `NullProviderAuditPort`, `InMemoryProviderAuditLog`) | Structured audit trail of every provider attempt/success/failure |
| `JsonHttpClient` / `UrllibJsonHttpClient` | Reusable HTTP GET + JSON parsing for adapters |
| `RateLimiter`, `CircuitBreaker`, `RetryPolicy` | Re-exported from `market_quote.service` — resilience is not reimplemented per domain |

## Vendors implemented

| Vendor | News | Filings | Ownership | Insider Trading | ESG | Transcripts |
|---|---|---|---|---|---|---|
| Yahoo Finance | ✅ | | ✅ | ✅ | ✅ | |
| Alpha Vantage | ✅ | | | | | |
| Financial Modeling Prep | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Polygon | ✅ | | | | | |
| SEC EDGAR | | ✅ | | ✅ | | |
| NSE | | ✅ | ✅ | ✅ | | |
| BSE | | ✅ | ✅ | ✅ | | |
| Screener | | ✅ | ✅ | | | |
| Null (fallback) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| InMemory (tests / self-hosted feed) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

TwelveData is deliberately not wired to any of these six domains — it is a
market-data/technical-indicators vendor and does not offer news, filings,
ownership, insider trading, ESG, or transcript data; adding it here would
mean hardcoding a non-existent capability. It remains available for future
market-data domains via the same adapter pattern.

Providers are tried in **priority order** (lower number = higher priority,
mirroring `PriorityProviderRegistry`); disabled/misconfigured providers are
skipped without failing the request, and `FailoverGroup` moves to the next
candidate automatically. When every configured provider fails or none are
configured beyond `Null`, endpoints return HTTP 200 with `available: false`
and `"Data unavailable."` — never fabricated content.

## Additive API routes (thin routers, no business logic)

| Domain | Data route | Health route |
|---|---|---|
| News | `GET /api/v1/news?symbol=` | `GET /api/v1/news/health` |
| Filings | `GET /api/v1/filings?symbol=` | `GET /api/v1/filings/health` |
| Ownership | `GET /api/v1/ownership?symbol=` | `GET /api/v1/ownership/health` |
| Insider Trading | `GET /api/v1/insider-trading?symbol=` | `GET /api/v1/insider-trading/health` |
| ESG | `GET /api/v1/esg?symbol=` | `GET /api/v1/esg/health` |
| Transcripts | `GET /api/v1/transcripts?symbol=` | `GET /api/v1/transcripts/health` |

Every router only calls `state.platform.get_authenticated_<domain>(...)` /
`state.platform.<domain>_health()` and maps the result to a public JSON
envelope (`ok`, `available`, `authenticated`, `identity`, `<data>`,
`provenance`, `attempted_provider_ids`, `message`). No aggregation,
scoring, or vendor-specific parsing lives in `api_platform`.

## Configuration (environment)

| Domain | Env vars |
|---|---|
| News | `DSP_NEWS_YAHOO_ENABLED`, `DSP_NEWS_ALPHAVANTAGE_API_KEY`, `DSP_NEWS_FMP_API_KEY`, `DSP_NEWS_POLYGON_API_KEY`, `DSP_NEWS_MEMORY` |
| Filings | `DSP_FILINGS_SEC_EDGAR_USER_AGENT`, `DSP_FILINGS_FMP_API_KEY`, `DSP_FILINGS_NSE_ENABLED`, `DSP_FILINGS_BSE_ENABLED`, `DSP_FILINGS_SCREENER_ENABLED`, `DSP_FILINGS_MEMORY` |
| Ownership | `DSP_OWNERSHIP_YAHOO_ENABLED`, `DSP_OWNERSHIP_FMP_API_KEY`, `DSP_OWNERSHIP_NSE_ENABLED`, `DSP_OWNERSHIP_BSE_ENABLED`, `DSP_OWNERSHIP_SCREENER_ENABLED`, `DSP_OWNERSHIP_MEMORY` |
| Insider Trading | `DSP_INSIDER_SEC_EDGAR_USER_AGENT`, `DSP_INSIDER_FMP_API_KEY`, `DSP_INSIDER_NSE_ENABLED`, `DSP_INSIDER_BSE_ENABLED`, `DSP_INSIDER_YAHOO_ENABLED`, `DSP_INSIDER_MEMORY` |
| ESG | `DSP_ESG_YAHOO_ENABLED`, `DSP_ESG_FMP_API_KEY`, `DSP_ESG_MEMORY` |
| Transcripts | `DSP_TRANSCRIPT_FMP_API_KEY`, `DSP_TRANSCRIPT_MEMORY` |

Default (no env vars set): every registry falls back to a single `Null`
adapter → all six endpoints honestly report `"Data unavailable."`.
`*_MEMORY=true` enables an in-memory adapter useful for self-hosted feeds,
staging, and tests (seeded via `adapter.put(bundle)`).

## Resilience per provider (via `*Service`)

Each provider is wrapped independently before entering the `FailoverGroup`:

- **Cache** — `InMemoryCache` keyed by query, configurable TTL
- **Rate limiting** — token-bucket `RateLimiter` (requests/minute)
- **Retry** — `RetryPolicy` with bounded attempts + backoff
- **Timeout** — enforced in the HTTP client layer
- **Circuit breaker** — `CircuitBreaker` opens after repeated failures, short-circuits until cool-down
- **Health** — `ProviderHealth` surfaced via `<domain>_health()` and `/<domain>/health`
- **Metrics** — request/success/failure/cache-hit counters via `<domain>_metrics()`
- **Audit logging** — every attempt, success, and failure recorded via `ProviderAuditPort`

`FailoverGroup` then tries each wrapped service in priority order and
returns the first successful, validated result, recording
`attempted_provider_ids` in the response for full transparency.

## Frontend wiring

`apps/web/src/lib/api/client.ts` exposes `api.news`, `api.filings`,
`api.ownership`, `api.insiderTrading`, `api.esg`, `api.transcripts` (plus
matching `*Health` calls and typed payloads). The workspace sections
consume them via React Query:

- `NewsSection` → `GET /news`
- `OwnershipSection` → `GET /ownership` (promoter/institutional holding) + `GET /insider-trading` (insider transactions)
- `DocumentsSection` → `GET /filings` (annual reports / quarterly results / investor presentations) + `GET /transcripts` (conference calls), alongside the existing `GET /corporate-actions`

When a provider is not configured, sections keep the pre-existing, honest
`"Data unavailable — no data source connected."` empty state — no
placeholder or mocked content is ever rendered.

## Testing

- `packages/data_engine/tests/test_connector_framework.py` — shared registry, failover, and field-value behavior
- `packages/data_engine/tests/test_{news,filings,ownership,insider_trading,esg,transcripts}.py` — adapters, validation, service resilience, registry ordering, env-based defaults (falls back to Null)
- `packages/dsp_platform/tests/test_*` — façade wiring (implicitly exercised by the API tests below)
- `packages/api_platform/tests/test_{news,filings,ownership,insider_trading,esg,transcripts}_api.py` — default unavailable state, authenticated payload shape, health endpoint
- `apps/web/src/components/company-analysis/sections/sections.test.tsx` — honest empty states and wiring for `OwnershipSection`, `NewsSection`, `DocumentsSection`

## Compliance

| Rule | Result |
|---|---|
| Ports & Adapters architecture followed | PASS |
| No business logic in API routers | PASS |
| Common interface per domain (`*ProviderPort`) | PASS |
| Provider registry + dependency injection | PASS |
| Provider priorities + automatic failover | PASS |
| Caching / retry / rate limiting / timeout / circuit breaker | PASS |
| Provider health + audit logging | PASS |
| Normalized models only; no vendor fields outside adapters | PASS |
| Missing data → `"Data unavailable."` (never fabricated) | PASS |
| No breaking API / engine changes (fully additive) | PASS |
| CV-001 / CV-002 | PASS |

## Final

**PASS** — production-ready, additive Data Connector Framework covering
News, Filings, Ownership, Insider Trading, ESG, and Transcripts, wired end
to end from adapters through to the workspace UI.
