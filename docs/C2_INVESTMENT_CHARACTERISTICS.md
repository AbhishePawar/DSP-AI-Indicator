# C2 — InvestmentCharacteristics (Decision Record)

**Status:** ACCEPTED · Incorporated into [C2_AIMF_ARCHITECTURE_FREEZE.md](C2_AIMF_ARCHITECTURE_FREEZE.md)  
**Parent freeze:** AIMF Architecture Freeze

## Decision

`InvestmentCharacteristics` is a first-class AIMF domain concept.

## Limited responsibility

Represents reusable investment archetypes and **default** investment philosophy only.

## Explicit non-responsibilities

Does **NOT**:

- replace `IndustryMethodology`
- define peer groups or comparable companies
- own `MetricApplicability` or `PeerEligibility`
- own industry-specific operating metrics
- own industry identifiers

## Binding rules

```
IndustryProfile → references InvestmentCharacteristics (defaults)
IndustryMethodology → bound to IndustryIdentity; may override defaults
```

Sharing characteristics never implies DIRECT / RELATED peers.

## Correct reuse example

| Industry | Characteristics | Own methodology |
|---|---|---|
| Utilities | Stable Regulated Cash Flow | Yes |
| Telecom Towers | Stable Regulated Cash Flow | Yes |

## Forbidden methodology sharing

Banks · Insurance · Stock Exchanges — never one shared `IndustryMethodology`.

## Compatibility

No required changes to DecisionPack, Universe, DSPPlatform, Committee, Recommendation, Valuation Engine, or analysis engines.
