# LOAD TEST REPORT — EPIC-018

| Field | Value |
|---|---|
| Epic | EPIC-018 |
| Date | 2026-08-03 |
| Branch | `cursor/p6-1-commercial-readiness` |
| Tip | `389d9b1` |
| Live cluster | **false** |
| Tooling | `scripts/perf/epic017_load_scenarios.py` via FastAPI `TestClient` |
| k6 / Docker / staging URL | **Unavailable** on validation host |

## Honesty statement

Results are **synthetic in-process concurrency**, not multi-host production capacity. Research/valuation analyse paths were **not** load-tested (architecture freeze; health/ready focus matches EPIC-017 ops posture). Do **not** use these numbers to claim production P95 SLOs are met.

## Workloads attempted

| Target surface | Exercised? | Notes |
|---|---|---|
| Health / ready | Yes | Primary synthetic path |
| Analyse / research engines | No | Freeze + no live cluster |
| Enterprise API (authz-heavy) | No | Not in synthetic script |
| Auth login/refresh | No | Cookie/IdP live path unavailable |

## EPIC-018 fresh run (100 / 500 / 1000 VU)

Artefact: `docs/audit/load_test_results_epic018.json`

| Users | Requests | Failures | Error rate | Throughput RPS | Mean ms | P50 ms | P95 ms | P99 ms | Max ms |
|---|---|---|---|---|---|---|---|---|---|
| 100 | 300 | 0 | 0.0 | 62.63 | 904 | 679 | 2576 | 3368 | 3809 |
| 500 | 1500 | 0 | 0.0 | 56.15 | 1109 | 752 | 3402 | 4748 | 7520 |
| 1000 | 3000 | 0 | 0.0 | 48.37 | 1303 | 897 | 3891 | 5888 | 12190 |

## Prior EPIC-017 5000 VU (unchanged evidence)

Artefact: `docs/operations/load_test_results_epic017.json`

| Users | Requests | Failures | P95 ms | P99 ms | Throughput RPS |
|---|---|---|---|---|---|
| 5000 | 15000 | 0 | 6459 | 10353 | 29.26 |

## Resource / dependency latency

| Signal | Result |
|---|---|
| Host CPU / mem under load | Not instrumented (local Windows agent host) |
| Postgres latency | **N/A** — not connected in TestClient synthetic path |
| Redis latency | **N/A** — not exercised |
| Error budget | 0 synthetic failures at all VU levels |

## Bottleneck hypotheses (unchanged)

1. Single-process GIL / shared TestClient understates horizontal scale  
2. Real Postgres pool saturation not measured  
3. Redis rate-limit / session ports dominate authenticated traffic in prod  
4. Research/valuation paths excluded by design  

## Optimisation

**None performed.** EPIC-018 forbids optimisation without production evidence. No code changes for performance.

## Verdict

| Question | Answer |
|---|---|
| Useful relative pressure signal? | Yes — 0 errors; latency rises with VU as expected |
| Production capacity certification? | **No** |
| Blocks Commercial GA? | Reinforcing **HIGH** residual (AUD-011); not sole CRITICAL, but insufficient for GA performance claim |
