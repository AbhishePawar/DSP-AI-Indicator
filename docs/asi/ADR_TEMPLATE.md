# ADR Template (ASI)

| Field | Value |
|---|---|
| **Template version** | `1.0.0` |
| **Use** | Every significant architecture decision under ASI |
| **Index** | Link from [DSP_DECISION_RECORDS.md](../DSP_DECISION_RECORDS.md) |
| **Storage** | `docs/adr/ADR-XXXX-short-title.md` |

Copy this file for each new ADR. Replace placeholders. Do not leave sections empty — write `N/A` with rationale if truly unused.

---

```markdown
# ADR-XXXX: <Title>

| Field | Value |
|---|---|
| **Status** | Proposed \| Accepted \| Superseded \| Deprecated \| Rejected |
| **Date** | YYYY-MM-DD |
| **ASI task** | ASI-00N |
| **Authors** | |
| **Related** | links to packages / prior ADRs / freeze docs |

## Title

One-line decision name.

## Context

What is the current repository / architecture situation?

## Problem Statement

What concrete problem must be solved? Why now?

## Evidence

Facts from code, tests, CI, freeze docs, metrics dashboard, or audits.
(Bullet list; cite paths.)

## Options Considered

### Option A — <name>
- Description
- Pros
- Cons

### Option B — <name>
- Description
- Pros
- Cons

### Option C — <name> (optional)
- Description
- Pros
- Cons

## Selected Decision

Clear statement of what will be done (and what will not).

## Decision Rationale

Why the selected option wins given DSP freeze rules and integrity > features.

## Trade-offs

What we accept by choosing this option.

## Migration Plan

Steps, order, unlock scope, validation gates, re-freeze.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| | | | |

## Expected Impact

On architecture, packages, CI, docs, debt score, and operator workflow.

## Rollback

Link to task rollback plan ([ROLLBACK_TEMPLATE.md](ROLLBACK_TEMPLATE.md)).
Summary of how to reverse this decision if it fails validation.

## Status History

| Date | Status | Note |
|---|---|---|
| YYYY-MM-DD | Proposed | |
```

---

## When an ADR is required (ASI)

Create an ADR if the change:

- Alters package boundaries, dependency rules, or public export policy  
- Expands the ASI unfreeze list  
- Changes CI install/test topology in a material way  
- Introduces a new governance convention (versioning, coverage policy, arch-test standard)  
- Is difficult to reverse without a documented plan  

Skip ADR for trivial doc typos or single-package README fills that follow existing patterns.
