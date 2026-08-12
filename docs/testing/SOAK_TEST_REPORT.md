# SOAK TEST REPORT — EPIC-019A

| Field | Value |
|---|---|
| Date | 2026-08-04 |
| Script | `scripts/perf/soak_test.py` |
| Artefact | `docs/testing/soak_test_results_epic019a.json` |
| Target | 8–24h continuous production soak |
| Achieved this host | **PARTIAL** — **180.01 s (~3 min)** synthetic in-process TestClient |

## Honest duration

This agent/CI host cannot sustain an 8–24h multi-node soak in-session. Longest feasible executed here: **3 minutes**, 35 samples, **0 failures**.

| Metric | Value |
|---|---|
| Mode | `testclient` (in-process) |
| Paths | `/health`, `/health/ready`, `/health/live` |
| Samples | 35 |
| Failures | 0 |
| live_cluster | false |
| redis_observed | false |
| postgres_observed | false |
| tracemalloc peak | ~2939 KB |
| RSS (psutil) | unavailable (psutil not installed) |

## Ops 8–24h command (do not invent results)

```bash
# 8 hours
python scripts/perf/soak_test.py --hours 8 --interval-seconds 15 --out docs/testing/soak_test_results_ops.json

# Against staging URL
python scripts/perf/soak_test.py --hours 8 --base-url https://staging.example --paths /health,/health/ready,/health/live
```

Capture CPU/memory/connection counts from the host/orchestrator during ops runs. Attach Redis/Postgres metrics only when those services are actually in the path.

## Status

| Claim | Result |
|---|---|
| Reusable soak harness checked in | **PASS** |
| 8h live cluster soak evidenced here | **FAIL / NOT RUN** |
| EPIC-018 AUD-010 closure | **PARTIAL** (harness + short evidence; full duration = ops prerequisite) |
