# EPIC-A002 — Portfolio Intelligence Architecture

```
POST /api/v1/portfolio/intelligence
   portfolio / watchlist + research_objects / reports / snapshots
        ↓
PortfolioLoader / WatchlistLoader
        ↓
ResearchLinker (caller-supplied R001/R002/R004 only)
        ↓
Summaries (allocation / concentration / MoS / quality / risk lists)
        ↓
Citations + provenance + audit
```

No providers, engines, valuation math, scoring, or trade generation.
