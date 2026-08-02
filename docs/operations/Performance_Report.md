# Performance Report (EPIC-017)

**Claim:** Synthetic / offline load validation executed where environment allows.  
**Not claimed:** Live 5000-user production cluster certification.

## Methodology

| Method | Script | What it measures |
|---|---|---|
| In-process concurrency | `scripts/perf/epic017_load_scenarios.py` (wraps `load_test.py`) | `/health/ready` via FastAPI `TestClient` |
| Optional k6 | `scripts/perf/k6_health_load.js` | Live HTTP against BASE_URL |
| Memory snapshot | `scripts/perf/memory_snapshot.py` | Process RSS (ops) |

**Excluded by design (architecture freeze):** valuation engines, research analyse paths, recommendation scoring.

## Scenarios

Target VU ladder: **100 / 500 / 1000 / 5000** virtual users.

```bash
python scripts/perf/epic017_load_scenarios.py \
  --scenarios 100,500,1000,5000 \
  --requests-per-user 3 \
  --out docs/operations/load_test_results_epic017.json
```

Live (when cluster available):

```bash
k6 run -e BASE_URL=http://127.0.0.1:8000 -e VUS=100 -e DURATION=60s \
  scripts/perf/k6_health_load.js
```

## Results

Results are written to `docs/operations/load_test_results_epic017.json` when the script runs.  
Populate the table below from that JSON after execution.

| Users | Requests | Failures | Mean ms | P95 ms | P99 ms | Throughput rps | Notes |
|---|---|---|---|---|---|---|---|
| 100 | 300 | 0 | 1070.5 | 3371.3 | 4693.2 | 53.6 | Synthetic TestClient |
| 500 | 1500 | 0 | 1199.2 | 3588.6 | 5513.9 | 52.2 | Synthetic TestClient |
| 1000 | 3000 | 0 | 1291.1 | 3807.6 | 5537.4 | 48.8 | Single-process caveat |
| 5000 | 15000 | 0 | 2179.6 | 6459.2 | 10353.2 | 29.3 | Relative pressure only |

Source: `docs/operations/load_test_results_epic017.json` (2026-08-02 run). Zero failures; P95/P99 reflect in-process contention, **not** multi-node capacity.

## Bottlenecks (honest hypotheses)

1. **Single-process TestClient** — understates horizontal pod scale; overstates GIL contention.
2. **Postgres pool** — not exercised by health-only synthetic load; likely first real bottleneck under auth/enterprise traffic.
3. **Redis rate-limit/session** — hot path under authenticated concurrency.
4. **Upstream data providers** — dominate research latency; out of EPIC-017 optimisation scope.
5. **No unjustified optimisation performed** — policy: evidence before change.

## Recommendations (ops only)

- Keep API HPA (CPU 70%) with minReplicas ≥ 2 (prod ≥ 3).
- Prefer managed Postgres + Redis before large VU marketing claims.
- Add k6 in CI against staging for health + auth login (not engines).
- Capture baseline research output hashes pre/post deploy for identity (not performance).

## Verdict

**Production-deployable performance validation scaffolding is in place.** Absolute capacity for 5000 concurrent real users requires a staging/prod-like cluster run — document those results here when available.
