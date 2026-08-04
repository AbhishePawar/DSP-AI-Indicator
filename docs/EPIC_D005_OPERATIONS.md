# EPIC-D005 — Unified Data Operations

## Health

```http
GET /api/v1/data/health
```

Returns aggregated `overall_ok`, `overall_authenticated`, and per-provider
snapshots (sorted keys).

## Bundle

```http
GET /api/v1/data/bundle?symbol=AAPL&include_historical_series=true&historical_series_kind=ohlcv
```

| Case | HTTP | Body |
|---|---|---|
| All unavailable (null providers) | 200 | sections `unavailable`, `retrieval.any_available=false` |
| Partial success | 200 | `retrieval.partial=true`, missing sections honest |
| Hard orchestrator failure | 503 | `message: "Data unavailable."` |

## Configuration

Uses existing D001–D004 env vars (`DSP_MARKET_QUOTE_*`,
`DSP_FINANCIAL_STATEMENT_*`, `DSP_CORPORATE_ACTIONS_*`,
`DSP_HISTORICAL_SERIES_*`). No new secrets required for the orchestrator itself.

## Observability

- Logger: `data_engine.data_orchestrator`
- Metrics: requests, sections_ok/unavailable/error, partial_responses
