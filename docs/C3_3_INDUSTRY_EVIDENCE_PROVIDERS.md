# Phase C3.3 — Industry Evidence Provider Framework

**Status:** Implemented · Execution contracts only · No interpreters / bundles / engine wiring

## Purpose

Resolve `IndustryEvidenceDefinition` ids into `EvidenceProviderResult` values
via deterministic provider contracts.

## Responsibilities

| Owns | Does not own |
|---|---|
| Provider metadata + capabilities | Interpretation / claim language |
| `supports` / `availability` / `resolve` | Financial statement calculation |
| Explicit availability states | Comparison / DecisionPack mutation |
| Placeholder illustrative adapters | EvidenceBundle assembly |

## Availability model

`AVAILABLE` · `UNAVAILABLE` · `NOT_APPLICABLE` · `INSUFFICIENT_DATA` · `ERROR`

Unavailable paths must not fabricate non-placeholder values.

## Lifecycle

Providers are versioned (`ACTIVE` …) like other IEF registries. Capabilities must
reference known evidence definition ids.

## Examples

`dsp.provider.decision_pack` · `fundamental` · `valuation` · `technical`  
Default resolve → `INSUFFICIENT_DATA` until real adapters exist.  
Optional `emit_placeholder=true` context extra yields an explicit placeholder.

## Non-goals

Interpreter, EvidenceBundle, DecisionPack integration, Comparison changes,
ranking, scoring, engine calls.

> **Note:** C3.4 adds the Interpreter Framework separately; this document remains
> the Provider contract reference.
