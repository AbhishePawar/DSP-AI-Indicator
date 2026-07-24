# Phase C2.4 — Peer Eligibility Framework

**Status:** Implemented · Structural gate only · No Comparison Engine

## Purpose

Answer only: **Should DSP compare these companies?**

Eligibility is a **structural** gate (identity / methodology / policy). It is
not analytical comparison, scoring, or ranking.

## Architecture

```
Instrument
    ↓  InstrumentIndustryRegistry
IndustryIdentity
    ↓  IndustryMethodologyRegistry
IndustryMethodology
    ↓  peer_policy ref
PeerEligibilityPolicy
    ↓  PeerEligibilityEvaluator
PeerEligibilityResult  (status + reasons)
```

Future Comparison Engine must consume only successful eligibility results.

## Eligibility states

| Status | Meaning |
|---|---|
| `DIRECT_PEER` | Same industry (policy-defined); comparable by default |
| `RELATED_PEER` | Explicitly related industries; comparable only if allowed |
| `LIMITED_COMPARISON` | Weak structural link; comparable only if allowed |
| `NOT_COMPARABLE` | Explicit refusal |
| `INSUFFICIENT_DATA` | Missing binding / methodology / policy |
| `UNKNOWN` | No rule matched (policy default may use this) |

Every result includes ≥1 `PeerEligibilityReason`.

## Philosophy

- **Structural vs analytical:** eligibility uses industry identity and policy
  tables only — never financial metrics.
- **Never silent:** unresolved instruments and cross-industry refusals are
  explicit.
- **Bidirectional:** pair evaluation runs both policies; the stricter status wins.
- **Group outcomes:** `ELIGIBLE` / `MIXED` / `INELIGIBLE` with exclusion text.

## Instrument resolution

`resolve_methodology_for_instrument()`:

```
Instrument → IndustryIdentity → IndustryMethodology → PeerEligibilityPolicy
```

Rejects missing bindings, missing methodologies, and unknown policy refs.

## Examples

- Banks × Banks → `DIRECT_PEER`
- Banks × NBFC → `RELATED_PEER`
- Banks × Software → `NOT_COMPARABLE` (with reason)

## Non-goals

Comparison Engine, ranking, scoring, metric calculations, portfolio intelligence.
