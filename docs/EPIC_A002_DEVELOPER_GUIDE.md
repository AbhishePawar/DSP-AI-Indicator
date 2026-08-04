# EPIC-A002 — Developer Guide

Supply holdings/watchlist plus a map of Research Objects (and optionally reports/snapshots).

```http
POST /api/v1/portfolio/intelligence
{
  "portfolio": {"portfolio_id": "pf-1", "holdings": [{"symbol": "AAPL", "weight": 1}]},
  "research_objects": {"AAPL": { "...": "R001 dict" }}
}
```

Do not expect the service to fetch quotes, run valuation, or optimise weights.
