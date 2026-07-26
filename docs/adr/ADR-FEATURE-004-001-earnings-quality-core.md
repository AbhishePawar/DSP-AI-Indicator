# ADR-FEATURE-004-001: Earnings Quality Core Domain (Phase 1)

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **Epic** | FEATURE-004 |
| **Related** | FEATURE-001…003 · `packages/earnings_quality/` |

## Title

Introduce top-level `earnings_quality` package (FEATURE-004); keep distinct from
`business_quality.EarningsQualityEngine` (F3.2); defer platform composition.

## Decision

Create `earnings_quality` **0.1.0** with six explainable dimensions consuming FA + BQ.
Register in monorepo tooling. Do not wire platform/API/frontend/AI Committee.

## Consequences

- Name collision avoided by package path: `from earnings_quality import …`
- Restatement feeds and forward forecast models deferred (TD-F007 / TD-A010)

## Rollback

Unregister and remove/revert `packages/earnings_quality/`.
