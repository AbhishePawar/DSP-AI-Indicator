# Backend Performance — EPIC-P7.3

**Date:** 2026-07-29 · **Backend:** `dsp_platform` **1.7.3**  
**Scope:** Ops/performance only — no analytical or API contract changes.

## Profile summary

| Area | Observation | Action |
|---|---|---|
| Startup / import | ~13s cold import of `api_platform.api.app` (Windows venv) | Documented; Docker image no longer installs `[dev]` tooling |
| `create_app()` | ~5 ms after import | Acceptable |
| Memory (tracemalloc) | ~49 MB peak for app factory | No leak signal on repeated `create_app` |
| CPU hotspots (ops path) | Health/metrics handlers dominate ops probes | Left frozen; analyse engines not exercised |
| Serialization | Prometheus text + JSON health payloads small | OK |
| Caching | Redis optional via `DSP_REDIS_URL`; health uncached by design | Keep |
| Dependency loading | Monorepo façade imports many packages at import time | Future: lazy façades (separate epic) |

## Optimisations applied (P7.3)

1. Docker backend installs `.[api]` instead of `.[dev]` (excludes black/mypy/pytest from runtime image).  
2. `PYTHONOPTIMIZE=1` in runtime image.  
3. Uvicorn keep-alive + concurrency limits via env (`DSP_UVICORN_*`).  
4. Multi-worker guarded (default 1) to protect in-memory rate-limit/beta state.

## API ops latency (TestClient, n=30)

| Endpoint | P50 | P95 | P99 |
|---|---|---|---|
| `/health` | 6.1 ms | 6.7 ms | 6.8 ms |
| `/health/live` | 5.5 ms | 7.1 ms | 10.3 ms |
| `/health/ready` | 10.0 ms | 11.5 ms | 11.7 ms |
| `/metrics` | 5.5 ms | 7.5 ms | 8.5 ms |

Raw: `docs/perf/api_benchmark.json`

## Recommendations

1. Measure against live uvicorn+Caddy on Linux for production SLOs.  
2. Consider lazy imports inside `dsp_platform.__init__` in a dedicated non-behaviour epic.  
3. Keep workers=1 unless Redis-backed shared limiters are enabled.

**Backend performance score:** **8.2 / 10**
