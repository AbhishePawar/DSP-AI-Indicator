# ADR-ASI-004-001: Thin local pyprojects for former root-owned packages

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **ASI task** | ASI-004 |

## Title

Add metadata-only `pyproject.toml` files for packages previously root-owned only.

## Context

Eight registered packages (`contracts`, `core`, `data_engine`, `dsp`,
`dsp_platform`, `fundamental`, `orchestration`, `snapshot_bridge`) lacked local
manifests. Versions lived only in `__version__`; VERSION_MATRIX could not cite
pyproject. Root `setuptools.packages.find` already discovered their `src/` trees.

## Problem Statement

Governance inconsistency: most packages declare version/deps locally; these eight did not.

## Evidence

ASI-004 audit: 8 × `NO_PYPROJECT` for registered packages; 0 version mismatches elsewhere.

## Options Considered

### Option A — Leave root-owned forever
- Pros: Minimal files
- Cons: Permanent governance gap

### Option B — Add thin manifests (name/version/description/license/deps)
- Pros: Aligns with standard; no code change
- Cons: More files to maintain

### Option C — Publish packages independently with full authors/URLs
- Pros: Publish-ready
- Cons: Out of scope; churn

## Selected Decision

**Option B.** Dependencies lists are evidence-based from AST first-party imports.

## Decision Rationale

Package governance without architecture redesign.

## Trade-offs

Manifest deps must stay in sync with allowlists (architecture tests updated).

## Migration Plan

Add pyprojects; update VERSION_MATRIX notes; update arch tests’ declared-deps assertions.

## Risks

Stale deps if imports change — mitigated by ASI-003 allowlists + tests.

## Expected Impact

Closes TD-A003; Governance Health ↑.

## Status

Accepted.
