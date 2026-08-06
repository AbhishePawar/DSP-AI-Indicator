# EPIC-D003 — Authenticated Corporate Actions Pipeline

Status: **COMPLETE**  
Priority: P0 · Core Infrastructure  
Supports: **CV-001** · **CV-002** · RS compliance (thin client honesty)

## Goal

Provide authenticated corporate actions retrieval and validation as the
canonical event feed — **without** adjusting prices, calculating impacts,
valuing, scoring, or recommending.

## Architecture

```
[Web thin client]
   GET /api/v1/corporate-actions?symbol=
        ↓
[api_platform]  corporate_actions.router  (no data_engine import)
        ↓
[dsp_platform]  DSPPlatform.get_authenticated_corporate_actions()
        ↓
[data_engine.corporate_actions]
   CorporateActionPort → Registry → Adapter
   CorporateActionService (cache, rate limit, retry, timeout, circuit breaker,
                           validation, provenance, metrics, logging, health)
```

**Action types:** stock_split · bonus_issue · dividend · rights_issue · buyback ·
merger · demerger · symbol_change · share_capital_change

**Additive routes:** `GET /corporate-actions`, `GET /corporate-actions/health`

## Configuration

| Env | Meaning |
|---|---|
| `DSP_CORPORATE_ACTIONS_API_KEY` | Auth for HTTP / memory |
| `DSP_CORPORATE_ACTIONS_BASE_URL` | With API key → HTTP adapter |
| `DSP_CORPORATE_ACTIONS_MEMORY` | `true` → in-memory authenticated adapter |

Default: **Null** → always `"Data unavailable."`

## Compliance

| Rule | Result |
|---|---|
| Authenticated only / no fabricated events | PASS |
| No adjusted prices / calculations / valuation | PASS |
| Missing → `Data unavailable.` | PASS |
| Invalid → Reject | PASS |
| Provenance + deterministic + thin | PASS |
| No breaking API / engine changes | PASS |
| CV-001 / CV-002 | PASS |

## Final

**PASS** — production-ready authenticated corporate actions path.
