# EPIC-D001 — Market Quote Operations

## Health

```http
GET /api/v1/market/health
```

Returns provider id, `healthy`, `authenticated`, and detail. Null provider is healthy but `authenticated: false`.

## Quote fetch

```http
GET /api/v1/market/quote?symbol=AAPL&exchange=NASDAQ
```

| Case | HTTP | Body |
|---|---|---|
| Missing / unauthenticated | 200 | `available: false`, `message: "Data unavailable."` |
| Authenticated hit | 200 | `available: true`, `fields`, `provenance` |
| Provider hard failure | 503 | `available: false`, `message: "Data unavailable."` |

## Runtime knobs (env)

See [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) — `DSP_MARKET_QUOTE_*`.

## Observability

- Logs: logger name `data_engine.market_quote`
- Counters: successes, failures, unavailable, cache_hits, circuit_opens
- Never log API keys

## Incident playbook

1. Check `/market/health` — is provider authenticated?
2. Confirm env keys present in the API process
3. If circuit open — wait recovery timeout or restart process after fixing upstream
4. Prefer Null (unavailable) over serving stale fabricated values
