# EPIC-A003 — Monitoring Architecture

```
Watchlist / Portfolio Registry (references only)
        ↓
Snapshot Tracker (baseline_snapshot_id / current_snapshot_id)
        ↓
R005 research_diff (read-only over R004 archive)
        ↓
Alert Model + Severity + Citations + Provenance + Audit
        ↓
Optional A002 baseline/current structural compare
        ↓
MonitoringEvaluateResult (deterministic, immutable)
```

## Sources (read-only)

- R001 Research Object (via archived snapshots)
- R002 Institutional Report (via archived snapshots)
- R004 Research Archive
- R005 Research Diff
- A002 Portfolio Intelligence result dicts (caller-supplied)

## Hard rules

- Consume existing artifacts only
- Never call providers or execute engines
- No valuation / scoring / optimisation / recommendations
- No data mutation of research artifacts
- Missing context → `"Data unavailable."`
- Every alert cites source sections
