# Phase C3.4 — Industry Evidence Interpreter Framework

**Status:** Implemented · Meaning contracts only · No bundles / DecisionPack / Comparison wiring

## Purpose

Transform `EvidenceProviderResult` values into structured `EvidenceObservation`
artifacts under Industry Methodology + Applicability context.

## Responsibilities

| Owns | Does not own |
|---|---|
| Interpretation rules-as-data | Provider retrieval |
| Deterministic claim language | Financial metric calculation |
| Observation severity / category / confidence labels | Ranking, scoring, peer comparison |
| Placeholder illustrative interpreters | EvidenceBundle assembly |

## Provider vs Interpreter

| Provider | Interpreter |
|---|---|
| Retrieves / exposes values | Assigns meaning |
| Emits availability states | Emits citable observations |
| Never interprets | Never calculates or compares |

## Interpretation philosophy

- Deterministic and reproducible for the same context
- Methodology-aware (requires methodology id/version)
- Explicit about gaps (`INSUFFICIENT_DATA`, `UNAVAILABLE`, …)
- Forbidden ranking/score language in observation text
- Qualitative confidence only (`unknown` / `low` / `medium` / `high`)

## Lifecycle

Interpreters are versioned (`ACTIVE` …) like other IEF registries.
Interpretation rules must reference known evidence definition ids.

## Examples

`dsp.interpreter.decision_pack` · `fundamental` · `valuation` · `technical`  
Placeholder observations only until real methodology templates exist.

## Non-goals

EvidenceBundle, DecisionPack integration, Comparison changes, Portfolio,
ranking, scoring, financial calculations, engine calls.

> **Note:** C3.5 adds the Evidence Bundle Framework separately; this document
> remains the Interpreter contract reference.
