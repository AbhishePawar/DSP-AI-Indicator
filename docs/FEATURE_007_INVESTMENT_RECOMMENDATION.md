# FEATURE-007 — Investment Recommendation Engine (Phase 1)

| Field | Value |
|---|---|
| **Version** | `1.0.0` |
| **Status** | **Complete** — awaiting approval |
| **Last updated** | 2026-07-26 |
| **Package** | `investment_recommendation` **0.1.0** |
| **ADR** | [ADR-FEATURE-007-001](adr/ADR-FEATURE-007-001-investment-recommendation.md) |

## Executive Summary

Phase 1 delivers a deterministic Investment Recommendation Engine in
`packages/investment_recommendation` only. It blends public valuation MoS signals
with Business Quality Aggregator and domain engines into an explainable
recommendation (`strong_sell` → `strong_buy`). Distinct from G1.3
`recommendation.RecommendationEngine`. No LLM/ML. No platform/API/UI/AI Committee.

## Decision methodology

| Component | Default weight |
|---|---|
| Business Quality | 0.40 |
| Valuation / MoS | 0.35 |
| Economic Moat | 0.08 |
| Management | 0.06 |
| Financial Strength | 0.05 |
| Earnings Quality | 0.03 |
| Growth Quality | 0.03 |

Hard gates block Strong Buy when price is materially above intrinsic value.

## Architecture impact

New package registered; `/api/v1` unchanged; platform not composed.

## Test results

**33 PASS** package suite · integrity PASS · smoke/cycles PASS

## Feature health score

**91 / 100**

## Remaining technical debt

- TD-F013 platform composition of `investment_recommendation`
- TD-F014 richer MoS / penalty schedule providers
- Prior TD-F001…F012

## Recommended next feature

After approval: platform composition epic **or** AI Committee integration — **do not start without approval**.
