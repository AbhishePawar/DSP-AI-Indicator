# EPIC-D002 — Authenticated Financial Statement Pipeline

Status: **COMPLETE**  
Priority: P0 · Core Infrastructure  
Supports: **CV-001** · **CV-002** · **RS-003**

## Goal

Provide authenticated financial statement retrieval and validation for research
surfaces and as the canonical statement feed for valuation engines — **without**
calculating ratios, scoring, valuation, or recommendations.

## Architecture

```
[Web thin client]
   GET /api/v1/fundamentals/statements?symbol=
        ↓
[api_platform]  fundamentals.router  (no data_engine import)
        ↓
[dsp_platform]  DSPPlatform.get_authenticated_financial_statements()
        ↓
[data_engine.financial_statement]
   FinancialStatementPort → Registry → Adapter
   FinancialStatementService (cache, rate limit, retry, timeout, circuit breaker,
                              validation, provenance, metrics, logging, health)
```

**Thin client preserved:** browser maps authenticated payloads or shows
`"Data unavailable."` / `"Unable to calculate."` — never invents or derives ratios.

**Additive only:** `/analyse` unchanged. New routes:

- `GET /fundamentals/statements`
- `GET /fundamentals/resolve`
- `GET /fundamentals/health`

### Components

| Layer | Responsibility |
|---|---|
| `FinancialStatementPort` | Provider interface + company resolution |
| `FinancialStatementProviderRegistry` | Named provider lookup |
| Adapters | `Null` / `InMemory` (auth + seeded) / `ConfiguredHttp` |
| `FinancialStatementService` | Resilience + cache + validation + metrics |
| Models | Periods (annual/quarterly/TTM), restated, currency, filing metadata |
| Validation | Reject fabricated source types; available↔null; mixed currencies |

### Data model

Annual · Quarterly · TTM · Restated · Reporting currency · Filing date · Fiscal year/quarter  
Income · Balance · Cash flow · Provider-supplied ratios (pass-through only)

## Configuration

| Env | Meaning |
|---|---|
| `DSP_FINANCIAL_STATEMENT_API_KEY` | Required for HTTP / memory auth |
| `DSP_FINANCIAL_STATEMENT_BASE_URL` | With API key → HTTP adapter |
| `DSP_FINANCIAL_STATEMENT_MEMORY` | `true` → in-memory authenticated adapter |

Default (unset): **Null** adapter — always `"Data unavailable."`

## Operations

See [EPIC_D002_OPERATIONS.md](EPIC_D002_OPERATIONS.md).

## Compliance

| Rule | Result |
|---|---|
| Authenticated statements only | PASS |
| No fabricated values | PASS |
| No calculations / valuation / scoring | PASS |
| Missing → `Data unavailable.` | PASS |
| Invalid → Reject | PASS |
| Provenance preserved | PASS |
| Deterministic / read-only / thin | PASS |
| CV-001 / CV-002 / RS-003 | PASS |
| No breaking API / engine changes | PASS |

## Final

**PASS** — production-ready authenticated financial statement path for RS-003.
