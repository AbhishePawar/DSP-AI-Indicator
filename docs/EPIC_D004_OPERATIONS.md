# EPIC-D004 — Historical Series Operations

## Health

```http
GET /api/v1/historical/health
```

## Series

```http
GET /api/v1/historical/series?symbol=AAPL&series_kind=ohlcv&frequency=daily&start_date=2024-01-01&limit=500
```

| Case | HTTP | Body |
|---|---|---|
| Missing / unauthenticated | 200 | `available: false`, `message: "Data unavailable."` |
| Authenticated hit | 200 | `available: true`, bars/points/snapshots + provenance |
| Provider hard failure | 503 | `available: false`, `message: "Data unavailable."` |

## Runtime knobs

`DSP_HISTORICAL_SERIES_API_KEY` · `DSP_HISTORICAL_SERIES_BASE_URL` ·
`DSP_HISTORICAL_SERIES_MEMORY` — see [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md).

## Observability

- Logger: `data_engine.historical_series`
- Counters: requests, cache_hits, successes, failures, unavailable, rejected_invalid
- Never log API keys
