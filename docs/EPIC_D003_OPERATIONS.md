# EPIC-D003 — Corporate Actions Operations

## Health

```http
GET /api/v1/corporate-actions/health
```

## Events

```http
GET /api/v1/corporate-actions?symbol=AAPL&action_type=dividend&start_date=2020-01-01&limit=50
```

| Case | HTTP | Body |
|---|---|---|
| Missing / unauthenticated | 200 | `available: false`, `message: "Data unavailable."` |
| Authenticated hit | 200 | `available: true`, `events`, `provenance` |
| Provider hard failure | 503 | `available: false`, `message: "Data unavailable."` |

## Runtime knobs

`DSP_CORPORATE_ACTIONS_API_KEY` · `DSP_CORPORATE_ACTIONS_BASE_URL` ·
`DSP_CORPORATE_ACTIONS_MEMORY` — see [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md).

## Observability

- Logger: `data_engine.corporate_actions`
- Counters: requests, cache_hits, successes, failures, unavailable, rejected_invalid
- Never log API keys
