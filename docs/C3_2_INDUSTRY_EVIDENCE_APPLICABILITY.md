# Phase C3.2 — Industry Evidence Applicability

**Status:** Implemented · Methodology-owned policy · No providers / interpreters

## Purpose

Bind `IndustryMethodology` to `IndustryEvidenceDefinition` via applicability
levels. The Evidence Registry remains definition-only.

## Ownership

| Concern | Owner |
|---|---|
| Evidence definitions | `IndustryEvidenceRegistry` |
| Applicability policy | **IndustryMethodology lineage** via `IndustryEvidenceApplicability` |
| Missing-evidence policy metadata | Applicability record |

## Applicability philosophy

Levels: `REQUIRED` · `RECOMMENDED` · `OPTIONAL` · `UNSUPPORTED` · `CONDITIONAL` · `UNKNOWN`

- One applicability lineage per methodology id
- Conflicting levels for the same evidence_id are rejected
- `RequiredEvidenceSet` cannot include `UNSUPPORTED` / `UNKNOWN`
- `CONDITIONAL` requires `condition_notes`
- `supported_industry_ids` on definitions are hints only — **this layer is authoritative**

## Methodology relationship

```
IndustryMethodology
        ↓
IndustryEvidenceApplicability (versioned)
        ↓
rules → IndustryEvidenceDefinition ids
```

## Validation

Unknown methodology / evidence · duplicate applicability · lineage conflicts ·
broken group refs · semver · lifecycle

## Examples

Commercial Banking · Electric Utilities · Premium Consumer Franchise  
(`seed_example_evidence_applicability_context`)

## Non-goals

Providers, interpreters, snapshots/bundles, comparison wiring, ranking, scoring.
