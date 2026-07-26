# ADR-ASI-002-003: Register `economic_moat` without enabling F4 analytics

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **ASI task** | ASI-002 |
| **Related** | `packages/economic_moat/` · ASI-001 unfreeze list |

## Title

Register the F4.1 `economic_moat` scaffold in root monorepo discovery tooling.

## Context

`economic_moat` 0.1.0 exists as an F4.1 framework shell (validation/metadata/
immutable models) but was absent from root `packages.find`, pytest `pythonpath`,
ruff, coverage, and isort first-party lists. ASI-001 explicitly allowed scaffolding
hygiene for this package with **no F4 analytics**.

## Problem Statement

An intentional package that is importable via manual path but invisible to
monorepo tooling is an integrity defect (orphan registration gap).

## Evidence

- Package has pyproject, src layout, README, tests
- `__version__` = 0.1.0
- Missing from all root registration lists (pre-ASI-002)
- Unfreeze list includes `packages/economic_moat/**` for hygiene only

## Options Considered

### Option A — Leave unregistered until Phase 4 product work
- Pros: Avoids implying readiness
- Cons: Continues integrity failure; tests harder to discover

### Option B — Register in root tooling; keep analytics frozen
- Pros: Fixes discovery; matches ASI-001 hygiene intent
- Cons: Slightly widens tool paths (acceptable)

### Option C — Move/rename package
- Pros: None for integrity
- Cons: Forbidden redesign

## Selected Decision

**Option B.** Register paths only. No scoring, providers, market data, or API
integration.

## Decision Rationale

Evidence-based integrity correction inside approved unlock scope.

## Trade-offs

Package becomes visible to pytest/ruff/coverage configuration earlier than
product Phase 4.

## Migration Plan

Add `packages/economic_moat/src` to root pyproject lists; list in VERSION_MATRIX
as scaffold 0.1.0; fix README broken link.

## Risks

Readers assume F4 is live — mitigated by README + STATUS freeze language.

## Expected Impact

Consistent monorepo discovery; TD-D005 partially resolved (registration);
remaining governance/docs polish may remain for ASI-004/005.

## Status

Accepted.
