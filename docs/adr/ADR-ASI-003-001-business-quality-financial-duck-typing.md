# ADR-ASI-003-001: Business Quality financial duck typing

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **ASI task** | ASI-003 |
| **Related** | `business_quality` · `financial` |

## Title

Preserve Business Quality’s duck-typed `FinancialAnalysis` inputs; do not add a hard import of `financial`.

## Context

`business_quality` declares `financial` in `pyproject.toml` but contains **no**
Python import of the `financial` package. Engines accept `Any` and validate
runtime type names / structure.

## Problem Statement

Architecture verification could “fix” the mismatch by importing `financial`
or by removing the declared dependency. Either change alters coupling without
an approved redesign.

## Evidence

- AST scan: `business_quality` first-party imports = `{core}` only
- Validators check type names such as `FinancialAnalysis`
- Package Health / Phase 3 freeze: FA-only composition by contract, not by import

## Options Considered

### Option A — Add `from financial import FinancialAnalysis`
- Pros: Declared dep matches imports
- Cons: Tightens coupling; touches frozen domain surface; redesign smell

### Option B — Remove `financial` from pyproject dependencies
- Pros: Honest declared graph
- Cons: May break install-order intent for consumers; metadata change → ASI-004

### Option C — Accept duck typing; allow `financial` in arch allowlist; document
- Pros: Preserves architecture; additive tests still forbid reverse edges
- Cons: Declared vs import asymmetry remains

## Selected Decision

**Option C.** Architecture tests allow `financial` but do not require it.
Metadata cleanup deferred to ASI-004 if desired.

## Decision Rationale

Architecture Preservation + Minimal Change. ASI-003 verifies; it does not redesign.

## Trade-offs

Dependency tools may still show `financial` as required without an import edge.

## Migration Plan

None for ASI-003.

## Risks

Future contributors may add a hard import casually — mitigated by freeze + reviews.

## Expected Impact

Stable BQ façade; clear ADR for auditors.

## Status

Accepted.
