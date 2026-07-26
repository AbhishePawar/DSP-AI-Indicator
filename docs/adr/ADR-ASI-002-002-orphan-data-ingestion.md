# ADR-ASI-002-002: Defer registration of empty `data-ingestion`

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **ASI task** | ASI-002 |
| **Related** | `packages/data-ingestion/` |

## Title

Do not register the empty `packages/data-ingestion` scaffold in root monorepo discovery.

## Context

ASI-002 inventory found `packages/data-ingestion/` with stub packages
(`adapters`, `pipelines`, `schedulers`) and an empty `__init__.py`. It is not
referenced in docs, VERSION_MATRIX, or root `pyproject.toml`.

## Problem Statement

An unregistered directory looks like an orphan. Blindly registering it expands
the monorepo public surface without ownership, tests, or product intent.

## Evidence

- Directory exists with stub modules only
- No documentation references found
- Not on ASI-001 unfreeze list for content changes
- Importable only when path is manually added

## Options Considered

### Option A — Register now in root pyproject
- Pros: Removes “orphan” appearance
- Cons: Implies supported package; no README/ownership; expands CI/test surface later

### Option B — Delete directory
- Pros: Clean tree
- Cons: Destructive; may discard intentional future scaffold; forbidden without explicit approval

### Option C — Document as deferred orphan; leave unregistered
- Pros: Honest integrity; no surface expansion; reversible
- Cons: Directory remains until ownership decision

## Selected Decision

**Option C.** Record as deferred technical debt. Future registration or removal
requires a dedicated ADR + unfreeze amendment.

## Decision Rationale

Minimal change; repository quality without inventing a package.

## Trade-offs

Orphan directory remains visible on disk.

## Migration Plan

None for ASI-002. Track as TD-D006.

## Risks

Someone may populate it without registration — mitigated by STATUS/debt visibility.

## Expected Impact

Clear ownership gap without premature coupling.

## Status

Accepted.
