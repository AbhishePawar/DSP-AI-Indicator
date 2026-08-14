# EPIC-R002 — Institutional Research Report Specification

Status: **COMPLETE**  
Priority: P0 · Research Infrastructure  
Schema: **1.0.0**  
Source: **Research Object v1.0.0 only**  
Supports: **CV-001** · **CV-002** · **CV-003** · **RS-001…RS-010**

## Goal

Generate the canonical Institutional Research Report exclusively from a
Research Object (EPIC-R001). Report generation only — no business decisions,
analytics, inference, scoring, valuation, or AI.

## Non-goals (DO NOT)

- Modify Research Object (R001), D001–D005, engines, scoring, valuation
- Breaking API changes
- Fabricate missing fields

## Section map

| Report section | RS | Research Object source |
|---|---|---|
| header | mandatory display | market + valuation + MoS + recommendation fields |
| executive_summary | RS-001 | identity + recommendation + metadata |
| market_data | RS-002 | market_data |
| financial_statements | RS-003 | financial_statements |
| corporate_actions | — | corporate_actions |
| historical_summary | — | historical_series |
| valuation | RS-004 | valuation |
| margin_of_safety | RS-005 | margin_of_safety |
| business_quality | RS-006 | business_quality |
| risk | RS-007 | risk |
| scenarios | RS-008 | scenarios |
| recommendation | — | recommendation |
| explainability | RS-009 | explainability |
| audit | RS-010 | audit + report generation metadata |

Missing → section `available: false` or field value `"Data unavailable."`  
`calculation_metadata` is always `"Data unavailable."` (R002 never calculates).

## Invariants

1. **Source** — Research Object only  
2. **Read-only** — frozen models + MappingProxyType  
3. **Aggregate / extract only** — known key lookup, never invent  
4. **Deterministic** — fixed `report_id` + `generated_at` → identical dicts  
5. **Thin** — HTTP validates and delegates  

## Version

```json
{
  "schema_version": "1.0.0",
  "report_version": "1",
  "generator_version": "1.0.0",
  "research_object_schema_version": "1.0.0"
}
```
