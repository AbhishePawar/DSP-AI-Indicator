# Phase C2.2 — Investment Characteristics Registry

**Status:** Implemented · Defaults only · No IndustryMethodology

## Purpose

Reusable economic archetypes that future `IndustryMethodology` objects may
inherit **defaults** from. Sharing characteristics never implies peers.

## Ownership

| Layer | Owner |
|---|---|
| Industry identity & hierarchy | `IndustryTaxonomy` / `IndustryIdentity` |
| Economic archetype defaults | `InvestmentCharacteristicsRegistry` |
| Optional industry→characteristics links | `IndustryProfile` / `IndustryProfileRegistry` |
| Metrics, peers, industry rules (future) | `IndustryMethodology` only |

## Responsibilities

| Owns | Does not own |
|---|---|
| Economic descriptors (capital intensity, cash-flow profile, …) | MetricApplicability |
| Soft valuation / dimension defaults | PeerEligibility |
| Versioned register / lookup / deprecate / validate | IndustryIdentity |
| Optional `IndustryProfile` references | ComparisonEngine / rankings |

## Relationship to IndustryMethodology

Characteristics are a **default layer only**. Methodology is authoritative.

```
methodology.assembled =
  methodology.overrides
    if present
    else characteristics.defaults
    else system defaults
metrics / peers = methodology only   # NEVER from characteristics
```

See [C2.3 Industry Methodology](C2_3_INDUSTRY_METHODOLOGY.md).

`IndustryProfile.characteristic_ids` never defines peer groups or methodology
ownership.

## Default / override rules

1. Characteristics supply guidance (`CharacteristicDefaults`) only.
2. Every default is overridable by methodology when that layer ships.
3. Zero characteristics on a profile is valid.
4. Unknown characteristic or industry references are rejected at register/validate.

## Example archetypes

- `dsp.characteristics.stable_regulated_cash_flow`
- `dsp.characteristics.pricing_power_franchise`
- `dsp.characteristics.asset_heavy_cyclical`
- `dsp.characteristics.capital_light_compounder`
- `dsp.characteristics.network_effects`

These are concepts only — not industry mappings.

## Non-goals

IndustryMethodology, peer comparison, rankings, scores, industry metrics,
valuation formulas, portfolio/risk.
