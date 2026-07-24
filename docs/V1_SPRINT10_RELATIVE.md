# V1.10 — Relative Valuation Suite

**Domain package:** `valuation` **`0.10.0`** · **Relative:** `0.10.0-relative`  

**Scope:** P/E, Forward P/E, PEG, P/B, P/TBV, P/S, P/CF, P/FCF, EV/Sales, EV/EBIT, EV/EBITDA, Dividend Yield — Industry / Sector / Peer / Historical / Weighted.

**Mode:** Research Mode only · Overall Valuation remains **DISABLED**

**Note:** Do **not** create git tags in this sprint — suite milestone tagging comes after Cross-Method Validation + Overall Valuation Aggregator.

---

## Objective

Implement a comprehensive Relative Valuation Suite on Valuation Core.
Does **not** modify existing valuation engines, Web VIE, or `/api/v1`.

Peer / industry / sector / historical multiples are **injected** via immutable
containers and a `MultipleProvider` port. No company names are hardcoded;
no market-data APIs are called.

---

## Module

```text
packages/valuation/src/valuation/relative/
  __init__.py
  relative_engine.py
  relative_models.py
  relative_validation.py
  relative_explainability.py
```

## Multiples

| Category | Multiples |
|---|---|
| Price | P/E, Forward P/E, PEG, P/B, P/TBV, Price/Sales, Price/CF, Price/FCF |
| Enterprise | EV/Sales, EV/EBIT, EV/EBITDA |
| Income | Dividend Yield |

## Benchmark scopes

| Scope | Fair multiple source |
|---|---|
| Industry | Industry median (else mean) |
| Sector | Sector median (else mean) |
| Peer | Peer median (else mean) |
| Historical | Historical / 5Y / 10Y average |
| Weighted | Weighted blend of industry / sector / peer |

## API

```python
from valuation import (
    ValuationEngine,
    RelativeInputs,
    RelativeMultiple,
    BenchmarkScope,
    BenchmarkMultiples,
)

result = ValuationEngine().analyze_relative(
    RelativeInputs(
        current_market_price=100,
        shares_outstanding=10,
        eps=5.0,
        method=RelativeMultiple.PE,
        benchmark_scope=BenchmarkScope.INDUSTRY,
        industry=BenchmarkMultiples(median=15.0, mean=16.0, count=12),
        peer=BenchmarkMultiples(median=13.0, count=6),
    )
)
assert result.implied_share_price.value is not None
```

## Peer abstraction

```python
from valuation import StaticMultipleProvider, RelativeMultiple, BenchmarkMultiples

provider = StaticMultipleProvider(
    industry={RelativeMultiple.PE: BenchmarkMultiples(median=15.0)},
    peer={RelativeMultiple.PE: BenchmarkMultiples(median=13.0, count=5)},
)
# Future Market Data Platform adapters implement MultipleProvider Protocol
```

## Shared Core

Uses Valuation Core: Validation, Confidence, Explainability, Scenario, Sensitivity engines.

## Suite readiness

Absolute methods + Relative Suite + Consensus are in place. Next: Overall Valuation Aggregator (V1.12), then suite git milestone.
