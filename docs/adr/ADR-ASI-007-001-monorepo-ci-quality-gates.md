# ADR-ASI-007-001: Monorepo CI quality gates

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **ASI task** | ASI-007 |

## Title

Make CI enforce integrity, architecture, monorepo smoke, and full package tests.

## Context

Historical CI ran pytest with coverage limited to `core`/`dsp` and lacked ASI-006
guards. Local GREEN (≈2299) diverged from CI fidelity (TD-D001).

## Problem Statement

Merges could pass CI while missing architecture/smoke/registration regressions.

## Evidence

Pre-ASI-007 workflow; ASI-006 smoke + 30 architecture modules; STATUS regression baseline.

## Options Considered

### Option A — Keep narrow core/dsp CI
- Cons: Continues TD-D001

### Option B — Full suite only, no staged gates
- Cons: Slower diagnosis

### Option C — Staged blocking gates: integrity → arch → smoke → full → lint/type
- Pros: Fast fail + full validation

## Selected Decision

**Option C.** Expand `dev` extras for HTTP/security test deps without changing product APIs.

## Decision Rationale

CI Parity Principle + Minimal Change.

## Trade-offs

Longer CI duration; matrix ×2 Python versions.

## Migration Plan

Update `ci.yml`, `Makefile`, add `scripts/ci_repository_integrity.py`, document in `docs/CI.md`.

## Risks

First remote run may surface environment-only failures — mitigated by local gate rehearsal.

## Expected Impact

Closes TD-D001 / TD-D005b (economic_moat included via registration + suite).

## Status

Accepted.
