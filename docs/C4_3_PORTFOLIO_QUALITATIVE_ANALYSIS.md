# Phase C4.3 — Portfolio Qualitative Analysis

**Status:** Implemented · Descriptive consumer only

## Qualitative philosophy

Portfolio Intelligence describes a portfolio in human-readable terms.
It does not score attractiveness, optimize weights, model risk, or recommend
trades.

## Consumer-only behavior

`PortfolioAnalyzer` reads:

- an assembled `Portfolio`
- optional DecisionPack / EvidenceBundle / ComparisonReport **references**

It never calls engines, interpreters, providers, or Comparison logic.
It never reinterprets EvidenceBundle observation payloads.

## Descriptor generation

Descriptors are qualitative labels across:

| Dimension | Example labels |
|---|---|
| Concentration | Highly concentrated / Moderately concentrated / Broadly diversified |
| Cash position | Fully invested / Moderate cash reserve / High cash reserve |
| Diversification | Broad / Limited / Single-sector exposure |
| Evidence coverage | Complete / Partial / Evidence gaps exist |
| Decision coverage | All holdings contain DecisionPacks / Missing DecisionPacks detected |
| Constraint notes | Constraint not evaluated / Constraint requires attention |

Concentration and cash labels use simple declared-weight / count heuristics
for wording only — they are **not** risk metrics.

Constraint notes never evaluate limits mathematically. Declared constraints
are reported as **not evaluated**, or as **requires attention** when required
descriptive inputs (weights / sector allocation / cash) are missing.

## Analysis pipeline

```text
Portfolio (+ optional citation overlays)
        ↓
validate_inputs()
        ↓
CoverageSummary
        ↓
PortfolioDescriptors + PortfolioObservations + ConstraintGapNotes
        ↓
PortfolioSummary + PortfolioReport
        ↓
PortfolioAnalysisResult
```

## API

- `analyze()` / `analyze_many()`
- `summarize()`
- `describe()`

## Non-goals

Optimization, risk (Sharpe / Beta / VaR), rebalancing, trading, ranking,
scoring, BUY/SELL/HOLD, and constraint evaluation engines.
