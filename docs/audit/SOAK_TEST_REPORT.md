# SOAK TEST REPORT — EPIC-018

| Field | Value |
|---|---|
| Epic | EPIC-018 |
| Date | 2026-08-03 |
| Target | 8–24 hours continuous production soak |
| Achieved | **PARTIAL** — synthetic in-process health soak |
| Live cluster | **false** |
| Artefact | `docs/audit/soak_test_results_epic018.json` |

## Honesty statement

This environment **cannot** sustain an 8–24h multi-node production soak (no Docker/Kubernetes, no staging URL). A longest-feasible synthetic soak was executed. Results are **not** invented 24h evidence.

## Execution

| Parameter | Value |
|---|---|
| Method | FastAPI `TestClient` continuous poll |
| Endpoints | `/health/live`, `/health/ready`, `/metrics` |
| Workers | 4 |
| Planned duration | 30 minutes (minimum PARTIAL band) |
| Wall-clock duration | **106.79 minutes** (~6407 s) |
| Samples | 432 |
| Failures | **0** |
| Error rate | 0.0 |
| P50 / P95 / P99 (ms) | 24.0 / 64.0 / 104.3 |
| Mean / Max (ms) | 28.6 / 127.4 |

### Sampling density note

Progress logs showed continuous sampling through ~t=543s (432 samples), after which wall-clock continued to ~107 minutes with no further sample growth — consistent with host/process stall (OneDrive/agent sleep) rather than healthy 107-minute high-frequency soak. **Do not over-claim continuous load density.** Failures remained 0 on collected samples.

## What was not proven

- Memory leak / RSS growth over 8–24h  
- Postgres connection pool exhaustion  
- Redis session/rate-limit drift  
- Multi-replica sticky session / CSRF cookie behaviour  
- Queue backlog / DLQ under sustained research jobs  
- GC / file descriptor growth  

## Residual risk

| ID | Risk | Severity |
|---|---|---|
| SOAK-R1 | Production soak 8–24h unevidenced | **HIGH** |
| SOAK-R2 | Sampling stall reduces confidence in long-window stability | MEDIUM |
| SOAK-R3 | Health-only path excludes analyse/enterprise/auth soak | HIGH |

## Verdict

| Status | **PARTIAL** |
|---|---|
| Acceptable for closed-beta pilot planning? | Conditionally informative only |
| Acceptable as Commercial GA soak evidence? | **No** |
| Invented 24h results? | **No** |
