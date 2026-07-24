# Phase C3.7 — Comparison Engine Evidence Integration

**Status:** Implemented · Consumer only · No ranking / scoring / reinterpretation

## Evidence integration philosophy

Comparison remains a **consumer** of Industry Evidence.

| Industry owns | Comparison does |
|---|---|
| Definitions, providers, interpreters, bundles | Cite supplied `EvidenceBundle` artifacts |
| Observation meaning | Copy observation title/summary into notes |
| Availability / gaps | Surface availability contrasts as coverage notes |

Comparison never calculates evidence, never interprets evidence, and never
embeds provider values.

## Flow

```text
DecisionPacks
    └─ optional EvidenceBundle[] (explicit injection)
            ↓
Peer eligibility + DecisionPack qualitative notes (C2.5)
            ↓
Validate bundles (instrument / methodology / digest vs pack refs)
            ↓
Cite observations + limitations + evidence summary
            ↓
ComparisonReport
```

## Fallback behaviour

When no bundles are supplied:

- C2.5 DecisionPack path continues unchanged
- Limitation `industry_evidence_not_supplied` is recorded
- Status is **not** degraded solely for missing optional evidence

## Report surface

- `evidence_summary` — coverage / availability / versions / digests
- `evidence_observations` — cited industry observations
- `evidence_limitations` — gaps / incomplete / missing peers
- Main `limitations` also includes evidence limitation codes for discoverability

Raw bundle entries and provider values are not exposed.

## Backward compatibility

`compare_packs(packs)` and `compare_universe_result(engine, result)` keep working.
Optional kwarg: `evidence_bundles=()`.

Platform: `DSPPlatform.compare_universe(..., evidence_bundles=())`.

## Non-goals

Portfolio, Risk, ranking, scoring, provider/interpreter/bundle redesign,
DecisionPack redesign, automatic bundle assembly inside Comparison.
