# ADR-FEATURE-001-001: Enable Economic Moat Core Analytics (Phase 1)

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **Epic** | FEATURE-001 |
| **Related** | [ADR-ASI-002-003](ADR-ASI-002-003-register-economic-moat.md) · `packages/economic_moat/` |

## Title

Unlock rule-based Economic Moat analytics inside `economic_moat` without expanding monorepo package boundaries.

## Context

ADR-ASI-002-003 registered the F4.1 scaffold with **analytics frozen**. ASI is closed.
FEATURE-001 authorizes the first post-ASI product epic: Phase 1 core moat engine.

## Problem Statement

The scaffold cannot score moat dimensions. Expanding analytics was explicitly deferred
to a new epic + ADR.

## Options Considered

### Option A — Keep scaffold; implement only in web EMI
- Pros: No Python change
- Cons: Violates FEATURE-001; duplicates methodology outside domain ownership

### Option B — Implement in `economic_moat` only; keep `dsp_platform` unwired
- Pros: Respects allowlists; additive API; matches BQ peer pattern
- Cons: Platform composition deferred

### Option C — Wire into `dsp_platform` immediately
- Pros: End-to-end path
- Cons: Requires platform allowlist ADR; out of FEATURE-001 “package only” scope

## Selected Decision

**Option B.** Implement six-dimension rule engine, evidence model, scoring, and
tests inside `economic_moat` **0.2.0**. Do not modify `dsp_platform` or other
packages. Do not invent new first-party dependencies.

## Decision Rationale

Matches FEATURE-001 scope, Package Governance, and Minimal Change Principle while
superseding the analytics freeze of ADR-ASI-002-003 for this package only.

## Consequences

- Public API expands additively (`MoatRating`, `MoatDimension`, component scores).
- `EconomicScore` now permits assessed numeric values (scaffold forbade scoring).
- Engine `analyze(...)` signature remains FA + BQ (+ optional weights/metadata).
- Platform composition and AI providers remain future ADRs.

## Rollback

Revert `packages/economic_moat` to tag/commit prior to FEATURE-001; restore
VERSION_MATRIX / STATUS notes to scaffold `0.1.0`.
