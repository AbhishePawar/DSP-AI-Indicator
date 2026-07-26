# ADR-ASI-004-002: Compliance empty dependencies

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **ASI task** | ASI-004 |
| **Related** | `packages/compliance/pyproject.toml` · TD-D008 |

## Title

Remove unused declared `core` dependency from `compliance`.

## Context

`compliance` declared `dependencies = ["core"]` but AST showed **no** first-party
imports (including `core`). Architecture tests already allowed `core` optionally.

## Problem Statement

Declared dependency graph was dishonest — governance integrity issue.

## Evidence

ASI-003/004 import scans: `compliance` first_party = `[]`.

## Options Considered

### Option A — Add a `core` import for honesty
- Cons: Touches domain code unnecessarily

### Option B — Remove unused dependency
- Pros: Honest metadata; minimal

### Option C — Leave as accepted soft dep
- Cons: Continues TD-D008

## Selected Decision

**Option B.** `dependencies = []`. Allowlist may still permit `core` if needed later (with dep update).

## Decision Rationale

Evidence-based metadata correction.

## Trade-offs

None material.

## Migration Plan

Edit pyproject; update architecture `test_declared_dependencies`.

## Risks

None — package never imported `core`.

## Expected Impact

Closes TD-D008.

## Status

Accepted.
