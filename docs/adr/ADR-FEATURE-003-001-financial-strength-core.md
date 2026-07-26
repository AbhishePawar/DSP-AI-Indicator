# ADR-FEATURE-003-001: Financial Strength Core Domain (Phase 1)

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **Epic** | FEATURE-003 |
| **Related** | FEATURE-001 · FEATURE-002 · `packages/financial_strength/` |

## Title

Introduce `financial_strength` as a self-contained Phase 1 domain; defer platform composition.

## Context

Third post-ASI analytical domain after Economic Moat and Management Quality.
Must remain package-only with no platform/API/frontend/AI Committee wiring.

## Decision

Create `financial_strength` **0.1.0** with six explainable dimensions consuming
`FinancialAnalysis` + `BusinessQualityAnalysis`. Register in monorepo tooling.
Do not compose into `dsp_platform`.

## Consequences

- Debt maturity / full stress history remain Phase 1 limitations (accepted TD-A009).
- Platform composition deferred (TD-F005).

## Rollback

Unregister paths and revert/remove `packages/financial_strength/`.
