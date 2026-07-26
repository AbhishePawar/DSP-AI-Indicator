# ADR-FEATURE-002-001: Management Quality Core Domain (Phase 1)

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **Epic** | FEATURE-002 |
| **Related** | FEATURE-001 · `packages/management_quality/` |

## Title

Introduce `management_quality` as a self-contained Phase 1 domain; defer platform composition.

## Context

Post-ASI feature work continues after Economic Moat Phase 1. Management quality is the
second core domain and must follow the same package-only integration rule.

## Problem Statement

No first-party package owned Buffett/Munger-style management / capital-allocation
assessment as an explainable composite distinct from Business Quality modules.

## Options Considered

### Option A — Extend `business_quality` only
- Pros: No new package
- Cons: Blurs BQ module ownership; harder to version management as its own product surface

### Option B — New `management_quality` package; reuse FA + BQ public outputs
- Pros: Clear ownership; mirrors FEATURE-001; no platform wiring
- Cons: Additional package registration

### Option C — Wire into `dsp_platform` / API immediately
- Pros: End-to-end path
- Cons: Out of FEATURE-002 scope; needs allowlist ADR

## Selected Decision

**Option B.** Register and implement `management_quality` **0.1.0** with six explainable
dimensions. Inputs remain `FinancialAnalysis` + `BusinessQualityAnalysis`. Do not modify
`dsp_platform` composition, API, or frontend.

## Consequences

- Root monorepo registration + smoke/cycle lists include `management_quality`.
- Governance and some integrity signals are confidence-/score-capped without board data.
- Platform composition deferred (TD-F003).

## Rollback

Remove package registration and delete/revert `packages/management_quality/`; restore
STATUS / VERSION_MATRIX entries.
