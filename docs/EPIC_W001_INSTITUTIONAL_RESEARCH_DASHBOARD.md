# EPIC-W001 — Institutional Research Dashboard

| Field | Value |
|---|---|
| **Status** | **COMPLETE (frontend implementation)** |
| **Date** | 2026-07-28 |
| **Type** | Major Product Implementation · P0 |
| **Surface** | `apps/web` `/research/institutional` |

## Summary

Production institutional research dashboard implementing **RS-001…RS-010** as
independently renderable sections over frozen `/api/v1/analyse`. Thin client
only — no engine, scoring, API, or governance-law edits.

## Architecture

See [DASHBOARD_ARCHITECTURE.md](DASHBOARD_ARCHITECTURE.md).

## Success criteria

| Criterion | Result |
|---|---|
| CV-001…CV-010 presentation compliance | PASS (honest unavailable / unable-to-calculate) |
| RS-001…RS-010 structural sections | PASS (mapper validation) |
| No placeholders / fabricated market quotes | PASS |
| Typed · testable · accessible landmarks | PASS |
| Deterministic mapper | PASS |
| Docs updated | PASS |

## Non-goals honoured

Engines · scoring · APIs · models · package boundaries · Core Values / Research Standards text · business logic — **unchanged**.
