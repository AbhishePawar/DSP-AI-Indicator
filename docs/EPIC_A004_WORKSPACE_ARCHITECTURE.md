# EPIC-A004 — Workspace Architecture

```
Caller-supplied artifacts
  R001 · R002 · R004 snapshots · R005 diffs
  A001 copilot · A002 portfolio · A003 monitoring
        ↓
DecisionWorkspaceService (aggregate only)
        ↓
Panels (deterministic order)
  research · report · timeline · active_alerts
  report_history · snapshot_history · diff_history
  copilot · portfolio · monitoring · audit
        ↓
Citations + provenance + audit metadata
```

Kinds: `company` | `portfolio` | `watchlist`

No providers, engines, calculations, valuation, scoring, optimisation, or mutation.
