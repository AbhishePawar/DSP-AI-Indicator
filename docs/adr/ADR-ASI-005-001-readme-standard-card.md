# ADR-ASI-005-001: Standard README card with optional appendix

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **ASI task** | ASI-005 |

## Title

Require a twelve-section README card on every package; preserve long historical detail as an appendix.

## Context

Eleven packages lacked READMEs. Several existing READMEs were short or idiosyncratic.
Long READMEs (e.g. `valuation`, `data_engine`) contain valuable freeze-era detail that
must not be destroyed.

## Problem Statement

Need uniform discoverability without deleting institutional documentation.

## Evidence

ASI-005 inventory: 11 missing; 0 relative link breaks after standardisation.

## Options Considered

### Option A — Rewrite every README from scratch
- Cons: Loses historical detail

### Option B — Only fill missing READMEs
- Cons: Inconsistent template compliance

### Option C — Standard card for all; append existing long content as appendix
- Pros: Uniform + preservative

## Selected Decision

**Option C.**

## Decision Rationale

Documentation excellence with minimal irreversible change.

## Trade-offs

Some packages have duplicated overview text (card + appendix). Acceptable.

## Migration Plan

Generator for missing/short; prepender for long; matrix + template published.

## Risks

Appendix drift vs card — mitigated by STATUS/VERSION_MATRIX as version truth.

## Expected Impact

100% README coverage; closes TD-D002 / TD-D007 (C4 notes).

## Status

Accepted.
