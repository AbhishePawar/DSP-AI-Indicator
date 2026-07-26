# ADR-ASI-002-001: Living version truth vs historical API RC

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **ASI task** | ASI-002 |
| **Related** | [VERSION_MATRIX.md](../VERSION_MATRIX.md) · [DSP_STATUS.md](../DSP_STATUS.md) · ADR-0012 |

## Title

Separate frozen HTTP/API RC identity from post-RC domain milestone tags.

## Context

STATUS labeled “Backend RC v2.0.0” while VERSION_MATRIX and K1.4 freeze docs
retain **v1.0.0-rc1** as the platform release candidate with `/api/v1`.
Domain work created tags `v2.0.0-financial-intelligence` and
`v3.0.0-business-quality` without a new HTTP RC.

## Problem Statement

Conflating milestone tags with API RC identity risks client contract confusion
and false “new RC” signals.

## Evidence

- [K1_4_PLATFORM_FREEZE.md](../K1_4_PLATFORM_FREEZE.md) freezes **v1.0.0-rc1**
- STATUS Project Health cited Backend RC **v2.0.0** alongside `/api/v1`
- Milestone tags exist for financial and business quality epics

## Options Considered

### Option A — Declare a new Backend RC v2.0.0
- Pros: Matches STATUS wording
- Cons: Implies API contract bump without release process; out of ASI integrity scope

### Option B — Clarify living docs: API RC remains v1.0.0-rc1; milestones separate
- Pros: Preserves freeze history; truthful; minimal change
- Cons: Requires STATUS wording correction

### Option C — Leave inconsistency
- Pros: None
- Cons: Continues integrity failure (TD-D004)

## Selected Decision

**Option B.** Living docs state:
- Platform API RC = **v1.0.0-rc1**
- Domain milestones remain named tags
- Historical regression counts stay historical; living count lives in STATUS

## Decision Rationale

Integrity and backward compatibility for clients; no silent RC inflation.

## Trade-offs

STATUS loses a shorthand “v2.0.0” label; gains accuracy.

## Migration Plan

Update STATUS + VERSION_MATRIX narrative only. No code/API changes.

## Risks

Readers may still skim historical docs; mitigated by VERSION_MATRIX living note.

## Expected Impact

Clear contract identity; closes version-narrative debt for ASI-002.

## Status

Accepted.
