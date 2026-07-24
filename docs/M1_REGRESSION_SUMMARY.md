# M1 Regression Summary — Management Intelligence Engine

**Date:** 2026-07-23 · **Web:** 2.1.0 · **MIE:** 1.0.0-mie-production

## Backend regression

```
1551 passed
```

**GREEN** — DSP platform pytest suite unchanged by MIE (frontend library only).

## MIE functional checks (M1.8)

| Check | Expected | Result |
|-------|----------|--------|
| `finalScoringEnabled` | true | PASS |
| Overall score from demo dashboard | number 0–100 | PASS (68 / Strong) |
| Weight sum | ≈ 1 | PASS |
| Aggregation = Σ contributions | within 0.15 | PASS |
| Deterministic re-run | identical score | PASS |
| Buffett `independentScore` | null | PASS |
| Dashboard validate | ok | PASS |
| Overall validate | ok | PASS |
| Evidence dedupe | unique ids | PASS |
| Frozen engines modified | none | PASS |

## Notes

- Category engines still expose `overallManagementScore(): null` locally (overall aggregation is centralized).
- Performance helpers in `miePerformance.ts` provide in-process latency samples (not CI SLA gates).
