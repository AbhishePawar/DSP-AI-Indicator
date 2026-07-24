# Phase C4.6 — Portfolio Monitoring

**Status:** Implemented · History tracking only

## Timeline philosophy

Portfolio Monitoring records how a Portfolio evolves across
`PortfolioSnapshot` points in time. It describes differences. It does not
judge investment quality.

## Snapshot evolution

```text
Portfolio.snapshots (+ optional current/previous overlays)
        ↓
ordered PortfolioTimeline (as_of, then snapshot_id)
        ↓
compare adjacent / explicit snapshot pair
        ↓
PortfolioChange records
        ↓
PortfolioMonitoringResult (+ enriched PortfolioReport)
```

## Change detection

Descriptive change kinds only:

- Holding added / removed
- Weight changed
- Cash changed
- Evidence coverage changed
- Decision coverage changed
- Constraint metadata changed (when previous constraints supplied)
- Snapshot recorded (initial)

## Consumer-only behavior

`PortfolioMonitor` may detect, describe, timeline, and summarize history.

It must **not**:

- recommend trades / BUY·SELL
- evaluate risk or calculate returns
- optimize allocation
- interpret evidence or execute comparison
- score or rank portfolios

## Report extensions (additive)

| Field | Role |
|---|---|
| `monitoring_summary` | Counts + status |
| `timeline` | Ordered snapshots |
| `recent_changes` | Latest descriptive changes |
| `monitoring_status` | EMPTY / INITIAL / UNCHANGED / CHANGED |

## Non-goals

Risk Intelligence, performance analytics, optimization, trading,
recommendations, return calculations, portfolio scoring.
