# Universe — Multi-Stock Decision Foundation (Phase C1)

Aggregates completed **Decision Packs** across an investment universe.

## Architecture position

```
InvestmentUniverse
        ↓
DSPPlatform.analyze_universe / MultiStockAnalysisService
        ↓
per instrument: analyze_decision_pack (canonical pipeline)
        ↓
MultiStockDecisionResult  (DecisionPack × N + failures)
        ↓
ComparableDecisionSummary (read-only; no ranking)
```

**Never** aggregates raw engine votes.

## Ownership

Package: `universe`  
Depends on: `contracts`, `core`, `decision_intelligence`  
Wired by: `dsp_platform` (composition root)

## Public API

```python
from datetime import date
from dsp_platform import (
    DSPPlatform,
    InvestmentUniverse,
    MultiStockAnalysisRequest,
    BatchFailurePolicy,
    summarize_decision_pack,
    filter_entries,
    group_entries,
)

universe = InvestmentUniverse(name="nifty-bank-watchlist")
universe.add(hdfc, tags={"nifty-bank"})
universe.add(icici, tags={"nifty-bank"})

result = platform.analyze_universe(
    MultiStockAnalysisRequest(
        universe=universe,
        start=date(2024, 1, 1),
        end=date(2024, 6, 30),
        failure_policy=BatchFailurePolicy.PARTIAL,
    )
)

for pack in result.packs:
    print(summarize_decision_pack(pack).action)
```

## Failure policy

| Policy | Behavior |
|--------|----------|
| `PARTIAL` | Continue after failures; status SUCCESS / PARTIAL_SUCCESS / FAILURE |
| `STRICT` | Stop after first failure; remaining instruments recorded as skipped failures (never silently omitted) |

## Filtering / grouping

Uses only explicit `Instrument.sector` / `industry` / `asset_class` and user tags.
No sector inference from names. No ranking.

## Out of scope (later phases)

Sector ranking, portfolio holdings, risk, behavioral, dashboard, LLMs.
