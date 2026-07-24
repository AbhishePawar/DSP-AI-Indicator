# L1.2 Sprint 1 — Company Analysis Workspace Foundation

**Web version:** `0.3.0`  
**Status:** Foundation complete (presentation over `/api/v1`)  
**Governance:** PR1.0–PR1.2 · Architecture Governance · User Trust · Constitution

---

## Scope delivered

Sections: Snapshot · Research Conclusion · Executive Summary · Investment Thesis ·
Business Quality · Financial Strength · Valuation · Decision Dashboard.

Trust UI: `SourceBadge` · `ValueCategoryBadge` · `ConfidenceBadge` · `EvidencePanel` ·
enhanced `MetricCard`.

## Thin client

- `POST /api/v1/analyze/company` (`as_decision_pack: false`)  
- Envelope mapped via `mapAnalyzeResponse` — **no browser math**  
- Missing fields → **Unavailable** (honest), educational metric copy only  

## Explicitly deferred

Analyst Consensus · DSP vs Street · AI Challenge · Knowledge Graph · Copilot ·
Evidence Explorer · Export logic

## Mobile

Accordion sections · sticky summary · metric stack · floating Copilot placeholder

## Quality notes

Research Mode terminology via `presentAction` / `presentFieldLabel`.  
Feature flags unchanged. Backend / API / compliance untouched.
