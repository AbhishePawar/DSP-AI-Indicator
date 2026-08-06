# EPIC-A003 — Monitoring Guide

## What it does

Reports **changes** between previously archived research snapshots and/or two
Portfolio Intelligence results. It does not generate new research.

## Typical flow

1. Archive research via R004 (`snapshot_id` baseline, then current).
2. Register symbols / portfolios on the monitoring registry (optional).
3. Track baseline/current snapshot ids (optional if you pass `snapshot_pairs`).
4. Call evaluate — receive alerts with severity, citations, provenance, audit.

## Severities

| Severity | Meaning |
|---|---|
| `info` | No material structural change signal |
| `watch` | Field-level changes outside important sections |
| `important` | Changes in valuation / MoS / risk / recommendation / quality (or MoS/missing research on portfolio) |
| `unavailable` | Snapshot or portfolio context missing |

## API sketch

```http
POST /api/v1/research/monitoring/evaluate
{
  "snapshot_pairs": {
    "AAPL": {
      "baseline_snapshot_id": "snap-a",
      "current_snapshot_id": "snap-b"
    }
  },
  "portfolio_intelligence_baseline": { "...A002 result..." },
  "portfolio_intelligence_current": { "...A002 result..." },
  "result_id": "mon-1",
  "created_at": "2026-07-28T12:00:00+00:00"
}
```
