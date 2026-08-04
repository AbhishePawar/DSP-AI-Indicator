# EPIC-D001 — Authenticated Market Data Integration

Status: **COMPLETE**  
Priority: P0 · Core Infrastructure  
Supports: **CV-001** (Data Authenticity First) · **RS-002** (Market Data section)

## Goal

Provide authenticated market quotes for research surfaces without inventing numbers, changing engines/scoring, or breaking `/api/v1/analyse`.

## Architecture

```
[Web thin client]
   GET /api/v1/market/quote?symbol=
        ↓
[api_platform]  market.router  (no data_engine import)
        ↓
[dsp_platform]  DSPPlatform.get_authenticated_market_quote()
        ↓
[data_engine.market_quote]
   MarketQuotePort → Registry → Adapter
   MarketQuoteService (cache, rate limit, retry, timeout, circuit breaker,
                       validation, provenance, metrics, logging, health)
```

**Thin client preserved:** browser never values or invents quotes; it only maps authenticated API payloads or shows `"Data unavailable."`

**Additive only:** `/analyse` unchanged. New routes: `GET /market/quote`, `GET /market/health`.

### Components

| Layer | Responsibility |
|---|---|
| `MarketQuotePort` | Provider interface |
| `MarketQuoteProviderRegistry` | Named provider lookup |
| Adapters | `Null` / `InMemory` (auth required + seeded) / `ConfiguredHttp` (API key + base URL) |
| `MarketQuoteService` | Resilience + cache + validation + metrics |
| `AuthenticatedMarketQuote` | RS-002 field set + provenance |
| Validation | Reject fabricated source types; reject available+null |

### Market fields (RS-002)

Current Price, Open, High, Low, Previous Close, 52W High/Low, Volume, Avg Volume, Market Cap, Enterprise Value, Shares Outstanding, Dividend Yield, Beta — plus timestamp + source metadata.

## Configuration

| Env | Meaning |
|---|---|
| `DSP_MARKET_QUOTE_API_KEY` | Required for HTTP / memory auth |
| `DSP_MARKET_QUOTE_BASE_URL` | With API key → HTTP adapter |
| `DSP_MARKET_QUOTE_MEMORY` | `true` → in-memory authenticated adapter (tests/ops seeding only) |

Default (unset): **Null** adapter — always `"Data unavailable."` (healthy, unauthenticated).

See also: [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md), [EPIC_D001_MARKET_DATA_PROVIDER.md](EPIC_D001_MARKET_DATA_PROVIDER.md).

## Operations

- Health: `GET /api/v1/market/health`
- Metrics: process-local counters on `MarketQuoteService.metrics` (successes, failures, cache hits, unavailable, circuit opens)
- Logging: `data_engine.market_quote` structured events
- Failures: never fabricate; return unavailable or raise provider errors mapped to honest API responses

## Compliance

| Rule | Result |
|---|---|
| Authenticated data only | PASS |
| No fabricated values | PASS |
| Missing → `Data unavailable.` | PASS |
| Invalid → Reject | PASS |
| Provenance preserved | PASS |
| Deterministic | PASS |
| Engines/scoring/APIs (breaking) untouched | PASS |
| Thin architecture | PASS |
| CV-001 / RS-002 | PASS |

## Tests

- `packages/data_engine/tests/test_market_quote.py`
- `packages/api_platform/tests/test_market_api.py`
- `apps/web/.../mapInstitutionalDashboard.test.ts`

## Final

**PASS** — production-ready authenticated market-data path for RS-002 / CV-001.
