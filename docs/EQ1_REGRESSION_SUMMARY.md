# EQI Regression Summary — Earnings Quality Intelligence Engine

**Date:** 2026-07-23 · **Web:** 2.3.0 · **EQI:** 1.0.0 · **Sprint:** EQ1.8

## Backend regression

```
1551 passed
```

**GREEN** — DSP platform pytest suite unchanged by EQI (frontend library only).

## EQI functional checks (EQ1.8)

| Check | Expected | Result |
|-------|----------|--------|
| `EQI_VERSION` | `1.0.0` | PASS |
| `ProductionReady` / `FeatureComplete` / `RegressionPassed` | true | PASS |
| `overallEarningsQualityEnabled` | true | PASS |
| Overall score from demoComplete | number 0–100 | PASS |
| Weight sum | ≈ 1 | PASS |
| Aggregation = Σ contributions | within 0.15 | PASS |
| Deterministic re-run | identical score | PASS |
| Dashboard validate | ok | PASS |
| Overall validate | ok | PASS |
| conclusionEvidenceMap non-empty links | ok | PASS |
| Earnings Persistence in weights | absent | PASS |
| Frozen engines modified | none | PASS |
| Category scoring algorithms changed | none | PASS |

## Cross-platform compatibility

| Surface | Impact |
|---------|--------|
| Research Platform | Untouched |
| Advisor Platform | Untouched |
| Management Intelligence Engine | Untouched (independent) |
| Economic Moat Intelligence Engine | Untouched (independent) |
| Shared utilities / frozen engines | Untouched |

## Notes

- Performance helpers in `eqiPerformance.ts` provide in-process latency samples (not CI SLA gates).
- Sample (local): category demo ~0.18ms · scored categories ~4.4ms · aggregation ~0.17ms · dashboard ~0.14ms · deterministic=true
- Full certification: `runEqiProductionValidation()` — **16/16 gates PASS** on EQ1.8 certification run.
- Demo overall score: **69.6** (unchanged from EQ1.7 — no scoring/weight changes).
