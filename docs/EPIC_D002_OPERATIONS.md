# EPIC-D002 — Financial Statement Operations

## Health

```http
GET /api/v1/fundamentals/health
```

## Statements

```http
GET /api/v1/fundamentals/statements?symbol=AAPL&period_type=annual&limit=8&include_restated=true
```

| Case | HTTP | Body |
|---|---|---|
| Missing / unauthenticated | 200 | `available: false`, `message: "Data unavailable."` |
| Authenticated hit | 200 | `available: true`, `periods`, `provenance` |
| Provider hard failure | 503 | `available: false`, `message: "Data unavailable."` |

## Company resolve

```http
GET /api/v1/fundamentals/resolve?symbol=AAPL
```

## Runtime knobs

See [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) — `DSP_FINANCIAL_STATEMENT_*`.

## Observability

- Logger: `data_engine.financial_statement`
- Counters: requests, cache_hits, successes, failures, unavailable, rejected_invalid
- Never log API keys

## Incident playbook

1. Check `/fundamentals/health` — authenticated?
2. Confirm env keys on the API process
3. If circuit open — fix upstream, wait recovery, or restart
4. Prefer Null (unavailable) over fabricated filings
