# EPIC-A002 — Portfolio Guide

```python
from dsp_platform.portfolio_intelligence import evaluate_portfolio_intelligence

result = evaluate_portfolio_intelligence(
    portfolio={
        "portfolio_id": "pf-1",
        "holdings": [
            {"symbol": "AAPL", "weight": 0.6},
            {"symbol": "MSFT", "weight": 0.4},
        ],
    },
    watchlist={"watchlist_id": "wl-1", "symbols": ["IBM"]},
    research_objects={"AAPL": ro_aapl, "MSFT": ro_msft},
)
```

Missing linked research → `"Data unavailable."` on that holding.
Sector allocation sums **caller-provided weights** by sector labels from research identity.
MoS/quality/risk summaries are pass-through lists — no portfolio-weighted scores.
