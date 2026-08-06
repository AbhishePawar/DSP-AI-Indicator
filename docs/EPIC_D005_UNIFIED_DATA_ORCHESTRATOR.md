# EPIC-D005 — Unified Data Orchestrator

Status: **COMPLETE**  
Priority: P0 · Core Infrastructure  
Supports: **CV-001** · **CV-002**

## Goal

Aggregate authenticated D001–D004 services into one canonical **read-only**
gateway. No calculations, valuation, scoring, recommendations, or fabricated
values.

## Architecture

```
[Web thin client]
   GET /api/v1/data/bundle?symbol=
        ↓
[api_platform]  data.router
        ↓
[dsp_platform]  get_unified_data_bundle()
        ↓
[data_engine.data_orchestrator.DataOrchestrator]
   parallel fetch → market_quote
                  → financial_statements
                  → corporate_actions
                  → historical_series
   + resolve identity, aggregate provenance/health/retrieval status
```

Partial failures return HTTP 200 with per-section `status` (`ok` |
`unavailable` | `error`) and `"Data unavailable."` — never invented payloads.

## Additive routes

- `GET /api/v1/data/bundle`
- `GET /api/v1/data/health`

## Final

**PASS** — production-ready unified authenticated data gateway.
