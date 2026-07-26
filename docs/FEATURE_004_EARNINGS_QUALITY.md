# FEATURE-004 — Earnings Quality & Predictability (Phase 1)

| Field | Value |
|---|---|
| **Version** | `1.0.0` |
| **Status** | **Complete** — awaiting approval |
| **Last updated** | 2026-07-26 |
| **Package** | `earnings_quality` **0.1.0** |
| **ADR** | [ADR-FEATURE-004-001](adr/ADR-FEATURE-004-001-earnings-quality-core.md) |

## Executive Summary

Phase 1 delivers an explainable Earnings Quality engine in
`packages/earnings_quality` only. Six Buffett-aligned dimensions produce
component scores, overall score, and rating (`very_poor` → `excellent`). Distinct
from F3.2 `business_quality.EarningsQualityEngine`. No platform/API/UI wiring.

## Scoring methodology

| Dimension | Weight |
|---|---|
| Earnings Consistency | 0.18 |
| Earnings Quality | 0.20 |
| Margin Stability | 0.15 |
| Earnings Predictability | 0.17 |
| Accounting Quality | 0.15 |
| Long-Term Sustainability | 0.15 |

**Ratings:** `<40` very_poor · `≥40` poor · `≥55` average · `≥70` good · `≥85` excellent

## Architecture impact

New package registered; `/api/v1` unchanged; platform not composed.

## Test results

**23 PASS** package suite · integrity PASS · smoke/cycles PASS

## Feature health score

**91 / 100**

## Remaining technical debt

- TD-F007 platform composition of `earnings_quality`
- TD-F008 restatement / forward-estimate providers
- Prior TD-F001…F006

## Recommended next feature

After approval: fifth core domain **or** composition epic — **do not start platform/API/UI/AI Committee without approval**.
