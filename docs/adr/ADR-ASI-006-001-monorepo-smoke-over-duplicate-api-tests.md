# ADR-ASI-006-001: Monorepo façade smoke over duplicate public_api files

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **ASI task** | ASI-006 |

## Title

Use one monorepo public-API smoke suite plus architecture `__all__` checks instead of mass-adding near-duplicate `test_public_api.py` files.

## Context

Only five packages had dedicated `test_public_api.py`. Most packages already gained
`__all__` / `__version__` checks via ASI-003/004 architecture tests. ASI-006 prioritises
measurable regression protection over coverage-file proliferation.

## Problem Statement

Adding 20+ nearly identical public_api modules would increase maintenance without
proportional protection.

## Evidence

Architecture tests already resolve `__all__` for packages that have them.
Registration/import regressions are cross-cutting concerns.

## Options Considered

### Option A — Add `test_public_api.py` to every package
- Pros: Uniform file names
- Cons: Heavy duplication

### Option B — Rely only on existing per-package unit tests
- Cons: Gaps for packages missing arch tests; no single registration guard

### Option C — Close arch gaps + one monorepo smoke/determinism suite + critical façade spot-checks
- Pros: High signal, low duplication

## Selected Decision

**Option C.**

## Decision Rationale

Evidence-based testing; quality over quantity.

## Trade-offs

Some packages lack a file named `test_public_api.py` even though façade protection exists.

## Migration Plan

Add arch tests for `dsp`, `economic`, `fundamental`, `snapshot_bridge`; add
`dsp_platform/tests/test_asi_monorepo_smoke.py`.

## Risks

Smoke does not execute deep domain maths — intentional under freeze.

## Expected Impact

Testing Health ↑; registration regressions caught early.

## Status

Accepted.
