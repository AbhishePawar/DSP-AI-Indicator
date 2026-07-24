# Phase C3.5 — Industry Evidence Bundle Framework

**Status:** Implemented · Assembly / orchestration only · No DecisionPack or Comparison wiring

## Purpose

Assemble resolved provider results and interpreter observations into a
canonical `EvidenceBundle` for one instrument + methodology lineage.

## Bundle philosophy

- Bundles **orchestrate** existing evidence artifacts
- Bundles **never** calculate metrics
- Bundles **never** interpret evidence
- Bundles **never** compare companies
- Missing evidence is recorded explicitly; values are never fabricated

## Assembly pipeline

```text
Applicability (methodology policy)
        ↓
Provider.resolve (retrieval)
        ↓
Interpreter.interpret (meaning)
        ↓
EvidenceBundle (canonical artifact)
```

## Responsibilities

| Owns | Does not own |
|---|---|
| Entry assembly + digests | Metric calculation |
| Status / summary / limitations | Interpretation rules |
| MissingEvidencePolicy honor | Ranking / scoring |
| Stable `EvidenceBundleReference` | DecisionPack / Comparison mutation |

## Status model

`COMPLETE` · `PARTIAL` · `INCOMPLETE` · `EMPTY`

`HARD_FAIL` missing-evidence policy raises instead of emitting `INCOMPLETE`.

## Lifecycle

Bundle identity is deterministic for the same assembly context.
`EvidenceBundleReference` carries `bundle_id`, methodology lineage, digest, status.

## Non-goals

DecisionPack integration, Comparison integration, Portfolio, ranking,
scoring, financial calculations, engine adapters.
