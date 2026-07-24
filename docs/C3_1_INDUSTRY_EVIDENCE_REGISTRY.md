# Phase C3.1 — Industry Evidence Registry

**Status:** Implemented · Definitions only · No providers / interpreters / applicability

## Purpose

Canonical registries for `IndustryMetricDefinition` and
`IndustryEvidenceDefinition`. This is metadata ownership only.

## Responsibilities

| Owns | Does not own |
|---|---|
| Registration, lookup, deprecate, validate | Evidence calculation |
| Semver lifecycle | Interpretation / evaluation |
| Metric ↔ evidence id reference checks | Comparison / DecisionPack mutation |
| Banking + Utilities example fixtures | EvidenceApplicability (methodology; later) |

## Ownership

Per [C3.0A freeze](C3_0A_INDUSTRY_EVIDENCE_ARCHITECTURE_FREEZE.md): IEF definitions live in
`packages/industry/`. Comparison and Decision Intelligence only consume later.

## Lifecycle

`DRAFT → ACTIVE → DEPRECATED → RETIRED`  
`lookup_active` returns highest ACTIVE semver (`1.10.0` > `1.9.0`).

## Versioning

`MAJOR.MINOR.PATCH` via `industry.semver`. `EvidenceVersion` wraps the same rule.

## Non-goals

Providers, interpreters, snapshots/bundles assembly, methodology applicability,
ranking, scoring, portfolio.

## Usage

```python
from industry import seed_example_evidence_registries

metrics, evidence = seed_example_evidence_registries()
nim = evidence.lookup_active("dsp.evidence.nim_stability")
```
