# Phase C2.3 — Industry Methodology Registry

**Status:** Implemented · Policy ownership only · No Comparison Engine

## Purpose

`IndustryMethodology` is the **policy authority** for an industry: valuation
method preferences, comparison dimensions, metric-applicability placeholders,
and peer-eligibility policy references.

## Ownership

| Concern | Owner |
|---|---|
| Industry identity | `IndustryIdentity` |
| Economic defaults | `InvestmentCharacteristics` |
| Assembled investment policy | **`IndustryMethodology`** |
| Metric calculations | Future (not C2.3) |
| Peer eligibility rules | Future (refs only here) |
| Comparison / ranking | Future Comparison Engine |

## Merge rules (deterministic)

Precedence — highest wins:

```
IndustryMethodology
        ↓
InvestmentCharacteristics defaults
        ↓
System defaults
```

- `None` on methodology valuation/dimensions → fall through.
- Explicit methodology value (including empty dimension tuple) → methodology wins.
- Metrics and `peer_policy` are **never** taken from characteristics.
- Every resolved field records `MergeSource` + a `merge_trace` line (nothing silent).

Use `assemble_methodology()` or `IndustryMethodologyRegistry.assemble()`.

## Versioning

`MAJOR.MINOR.PATCH` only (`industry.semver`). Active lookup uses semantic
ordering (`1.10.0` > `1.9.0`). Same for characteristics and industry profiles.

## Example methodologies

- `dsp.methodology.commercial_banking`
- `dsp.methodology.electric_utilities`
- `dsp.methodology.premium_consumer_franchise`

## Non-goals

Comparison Engine, peer comparison execution, ranking, scoring, metric
formulas, portfolio/risk intelligence, Valuation Engine changes.

## Future extension

Peer Eligibility policies (C2.4+) and Comparison Engine consume assembled
methodology + DecisionPack + summaries — never industry `if` branches.
