# ADR-ASI-003-002: Evidence-based architecture allowlists

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **ASI task** | ASI-003 |

## Title

Freeze current first-party import edges via additive allowlist architecture tests.

## Context

Mandatory packages lacked uniform `test_architecture.py` coverage. Existing
domain packages already used AST forbidden-import guards. ASI-003 extends that
pattern without redesigning layers.

## Problem Statement

Without guards, future edits can introduce forbidden imports or cycles silently.

## Evidence

- Pre-ASI-003: 13 domain `test_architecture.py` files; critical engines uncovered
- AST inventory of mandatory packages’ first-party imports
- Monorepo cycle scan: **0 cycles**

## Options Considered

### Option A — Redesign dependency layers
- Forbidden under ASI-003

### Option B — Document only
- Insufficient protection

### Option C — Additive allowlist tests matching current edges + cycle test
- Pros: Regression protection; minimal change
- Cons: Allowlist updates needed when intentional new edges are approved

## Selected Decision

**Option C.** Expanding an allowlist requires an ADR (significant architecture decision).

## Decision Rationale

Prevent regressions; preserve existing architecture.

## Trade-offs

Tests encode today’s graph; intentional new composition must update tests deliberately.

## Migration Plan

Add tests under each mandatory package; add monorepo cycle test under `dsp_platform`.

## Risks

False confidence if dynamic imports bypass AST — accepted residual; document if found.

## Expected Impact

Architecture Health ↑; TD-D003 largely closed for mandatory set.

## Status

Accepted.
