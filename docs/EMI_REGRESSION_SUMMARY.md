# EMI Regression Summary — Economic Moat Intelligence Engine

**Date:** 2026-07-23 · **Web:** 2.2.0 · **EMI:** 1.0.0 · **Sprint:** M2.8

## Backend regression

```
1551 passed
```

**GREEN** — DSP platform pytest suite unchanged by EMI (frontend library only).

## EMI functional checks (M2.8)

| Check | Expected | Result |
|-------|----------|--------|
| `EMI_VERSION` | `1.0.0` | PASS |
| `ProductionReady` / `FeatureComplete` | true | PASS |
| `overallMoatScoreEnabled` | true | PASS |
| Overall score from demoComplete | number 0–100 | PASS |
| Weight sum | ≈ 1 | PASS |
| Aggregation = Σ contributions | within 0.15 | PASS |
| Deterministic re-run | identical score | PASS |
| Dashboard validate | ok | PASS |
| Overall validate | ok | PASS |
| conclusionEvidenceMap non-empty links | ok | PASS |
| Distribution Advantage in weights | absent | PASS |
| Frozen engines modified | none | PASS |
| Category scoring algorithms changed | none | PASS |

## Cross-platform compatibility

| Surface | Impact |
|---------|--------|
| Research Platform | Untouched |
| Advisor Platform | Untouched |
| Management Intelligence Engine | Untouched (independent) |
| Shared utilities / frozen engines | Untouched |

## Notes

- Performance helpers in `emiPerformance.ts` provide in-process latency samples (not CI SLA gates).
- Sample (local): category demo ~0.2ms · scored categories ~3ms · aggregation ~0.3ms · dashboard ~0.1ms · deterministic=true
- Full certification: `runEmiProductionValidation()` — 16/16 gates PASS on M2.8 certification run.
