# P7.3 — Performance, Scalability & Production Optimisation Report

**Date:** 2026-07-29  
**Backend:** `1.7.3` · **Frontend:** `2.0.3` · **API:** `v1.0.0` (unchanged behaviour)  
**Certification:** `scripts/ops/certify_p7_3.py`  
**Decision:** **GO WITH CONDITIONS**

---

## Executive Summary

P7.3 establishes automated API latency benchmarks, concurrent load scenarios (10–500 users), and memory/startup snapshots for ops surfaces. Production image/runtime tuning reduces Docker dependency bloat and adds concurrency controls. Analytical engines and `/api/v1` contracts were **not** modified.

---

## Benchmark Results

### Sequential API (TestClient)

| Endpoint | P50 | P95 | P99 |
|---|---|---|---|
| `/health` | 6.1 ms | 6.7 ms | 6.8 ms |
| `/health/ready` | 10.0 ms | 11.5 ms | 11.7 ms |
| `/metrics` | 5.5 ms | 7.5 ms | 8.5 ms |

### Load scenarios (`/health/ready`, 3 req/user)

| Users | RPS | P50 | P95 | Failures |
|---|---|---|---|---|
| 10 | 77 | 98 ms | 221 ms | 0 |
| 50 | 68 | 407 ms | 1.56 s | 0 |
| 100 | 65 | 667 ms | 2.26 s | 0 |
| 500 | 56 | 790 ms | 3.27 s | 0 |

Artifacts: `docs/perf/api_benchmark.json`, `docs/perf/load_test_results.json`

---

## Resource Usage

| Metric | Value |
|---|---|
| Import `create_app` module | ~12.9 s cold (venv) |
| `create_app()` | ~4.8 ms |
| Tracemalloc peak | ~49 MB |
| Repeat create deltas | non-growing (no leak signal) |

---

## Optimisations Applied

1. Backend image: `pip install -e ".[api]"` (not `[dev]`)  
2. `PYTHONOPTIMIZE=1`  
3. Uvicorn keep-alive + concurrency env knobs; workers default 1  
4. Next static cache headers + `optimizePackageImports` for lucide-react  
5. Perf scripts under `scripts/perf/`

---

## Scalability Assessment

| Dimension | Score | Notes |
|---|---|---|
| Ops endpoint latency | 9 | Sub-12 ms P99 sequential |
| Concurrent health load | 7 | Latency rises with concurrency (single-process TestClient/CPU bound) |
| Horizontal scale readiness | 7 | Needs Redis-backed limits before multi-worker |
| Image/runtime efficiency | 8 | Dev tooling removed from image |
| **Scalability** | **7.8** | |

---

## Remaining Bottlenecks

1. Cold import of full `dsp_platform` façade (~13 s)  
2. In-memory rate limits block safe multi-worker  
3. Load numbers are in-process; production Caddy+uvicorn Linux numbers will differ  
4. DB path not stressed (by design — engines frozen)

---

## Recommendations

1. Run `scripts/perf/*` in CI nightly against a long-lived uvicorn.  
2. Add Redis-backed rate limiting before `DSP_UVICORN_WORKERS>1`.  
3. Lazy-load heavy façades in a future non-behaviour epic.  
4. Capture host CPU/RAM with Prometheus/cAdvisor during live load.

---

## Performance Score

**Overall:** **8.1 / 10**  
**Scalability Score:** **7.8 / 10**

## Infrastructure Readiness

| Area | Status |
|---|---|
| Offline API/load/memory harness | Ready |
| Production image slim (`.[api]`) | Ready |
| Static asset cache headers | Ready |
| Multi-worker + Redis rate limits | Conditioned |
| Live Caddy/uvicorn load numbers | Conditioned (P7.0 drills) |

## Remaining Risks

1. Cold import ~13 s can dominate cold starts / scale-to-zero.  
2. In-process load figures understate network and overstate lock contention vs real multi-process.  
3. Without Redis-backed limits, horizontal uvicorn workers are unsafe.  
4. Database path not load-tested (engines frozen by epic constraint).

## PASS / FAIL

**PASS** — benchmarks, load tests, DB review, memory analysis, docs, and certification gates completed without analytical/API regressions.

## Decision

**GO WITH CONDITIONS** — ship performance channel **1.7.3 / 2.0.3**; complete live multi-node load + Redis rate-limit before unrestricted horizontal scale.
