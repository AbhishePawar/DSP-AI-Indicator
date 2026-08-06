# EPIC-A004 — Workspace Guide

## Purpose

One read-only decision interface that surfaces existing research outputs together.
Missing panels return `"Data unavailable."`

## Build a company workspace

```http
POST /api/v1/decision/workspace
{
  "kind": "company",
  "subject": "AAPL",
  "research_object": { "...R001..." },
  "report": { "...R002..." },
  "snapshots": [{ "...R004..." }],
  "diffs": [{ "...R005..." }],
  "copilot_response": { "...A001..." },
  "monitoring_result": { "...A003..." },
  "workspace_id": "ws-1",
  "created_at": "2026-07-28T12:00:00+00:00"
}
```

## Portfolio / watchlist

Pass `kind=portfolio` or `kind=watchlist` with `portfolio_intelligence` (A002).
Other panels remain optional.

## Panels

Every panel includes citations. Workspace-level citations are the deduplicated union.
