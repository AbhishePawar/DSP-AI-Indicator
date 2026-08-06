# EPIC-D004 — Authenticated Historical Time-Series Pipeline

Status: **COMPLETE**  
Priority: P0 · Core Infrastructure  
Supports: **CV-001** · **CV-002**

## Goal

Provide authenticated historical time-series retrieval and validation as the
canonical history feed — **without** indicators, technical analysis, adjusted
prices, valuation, scoring, or recommendations.

## Architecture

```
[Web thin client]
   GET /api/v1/historical/series?symbol=&series_kind=
        ↓
[api_platform]  historical.router  (no data_engine import)
        ↓
[dsp_platform]  DSPPlatform.get_authenticated_historical_series()
        ↓
[data_engine.historical_series]
   HistoricalSeriesPort → Registry → Adapter
   HistoricalSeriesService (cache, rate limit, retry, timeout, circuit breaker,
                            validation, provenance, metrics, logging, health)
```

**Series kinds:** ohlcv · market_cap · volume · enterprise_value · fundamentals · ratios  
**Frequencies (OHLCV):** daily · weekly · monthly

**Additive routes:** `GET /historical/series`, `GET /historical/health`

## Configuration

| Env | Meaning |
|---|---|
| `DSP_HISTORICAL_SERIES_API_KEY` | Auth for HTTP / memory |
| `DSP_HISTORICAL_SERIES_BASE_URL` | With API key → HTTP adapter |
| `DSP_HISTORICAL_SERIES_MEMORY` | `true` → in-memory authenticated adapter |

Default: **Null** → always `"Data unavailable."`

## Final

**PASS** — production-ready authenticated historical series path.
