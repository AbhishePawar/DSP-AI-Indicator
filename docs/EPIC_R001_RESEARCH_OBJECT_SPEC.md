# EPIC-R001 — Canonical Research Object Specification

Status: **COMPLETE**  
Priority: P0 · Research Core  
Schema: **1.0.0**  
Supports: **CV-001** · **CV-002** · **CV-003** · **RS-001…RS-010**

## Goal

Define a single **immutable**, **read-only** Research Object that is the
canonical research contract for the platform. Aggregate existing authenticated
data (D005) and existing analysis / valuation / quality / risk outputs only.

## Non-goals (DO NOT)

- Engines, scoring, valuation logic, breaking API changes
- Governance / Core Values / Research Standards redesign
- D001–D005 infrastructure changes
- New calculations, AI reasoning, or fabricated fields

## Contract shape

| Section | Source | RS alignment |
|---|---|---|
| metadata | builder | header / audit |
| identity | D005 identity / request | RS-001 context |
| market_data | D005 `market_quote` | RS-002 |
| financial_statements | D005 | RS-003 |
| corporate_actions | D005 | RS-003 context |
| historical_series | D005 | RS-002/003 context |
| valuation | analysis stage / valuation_signals | RS-004 |
| margin_of_safety | recommendation_summary / signals | RS-005 |
| business_quality | analysis `business_quality_aggregator` | RS-006 |
| risk | analysis `risk` when present | RS-007 |
| scenarios | analysis `scenarios` when present | RS-008 |
| recommendation | analysis `recommendation_summary` | RS-001 |
| explainability | analysis `stage_summaries` | RS-009 |
| audit | aggregated ids / versions / retrieval | RS-010 |
| provenance | per-section provenance map | RS-010 |

Missing sections → `available: false`, `message: "Data unavailable."`  
Never invent numbers to satisfy an RS field.

## Invariants

1. **Immutable** — frozen dataclasses + `MappingProxyType` payloads  
2. **Read-only** — no mutation after build  
3. **Aggregate-only** — pass-through of existing dicts  
4. **Deterministic** — fixed `object_id` + `created_at` → identical dicts  
5. **Thin** — no browser valuation; API delegates to platform façade  
6. **Provenance-preserving** — timestamps and source types retained  

## Version

```json
{
  "schema_version": "1.0.0",
  "object_version": "1",
  "builder_version": "1.0.0"
}
```
