# ADR-RS-001 — Constitutional Research Standards (RS-001…RS-010)

| Field | Content |
|---|---|
| **Status** | **Accepted** |
| **Date** | 2026-07-28 |
| **ID** | ADR-RS-001 |
| **Related** | [RESEARCH_STANDARDS.md](../RESEARCH_STANDARDS.md) · [RS_001_TO_RS_010.md](../RS_001_TO_RS_010.md) · [CORE_VALUES.md](../CORE_VALUES.md) · ADR-CV-001 · ADR-CV-002-010 |

## Context

Core Values define behavioural law (authenticity, determinism, explainability).
They do not alone specify the **minimum sections and fields** every production
research report must contain. Without explicit Research Standards, reports can
omit Margin of Safety, risk, scenarios, or provenance while still appearing
“complete.”

## Decision

Adopt **Research Standards RS-001 … RS-010** as constitutional content law:

1. Executive Summary  
2. Authenticated Market Data  
3. Financial Statement Analysis  
4. Valuation  
5. Margin of Safety (prominent, never hidden)  
6. Business Quality  
7. Risk Analysis  
8. Scenario Analysis  
9. Explainability  
10. Audit & Provenance  

Plus a **mandatory header** displayed first (price, IV, MoS, fair-value range,
CAGR, confidence, overall score, research status, recommendation).

**Research Report Validation MUST verify all RS-001…RS-010. Missing section = FAIL.**

Unavailable fields use **Data unavailable.** / **Unable to calculate.** per
Core Values — never invent numbers to pass validation.

## Consequences

- Architecture Bible, Constitution, report/research specs, checklists, DoD,
  quality/release/production gates, Decision Records, PEP ADR register, README,
  and Cursor rules reference RS.  
- **No** engine, scoring, API, model, boundary, or business-logic changes in
  this ADR — governance documentation only.  
- Future report emitters must implement RS validation before production emit.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Soft “nice to have” sections | Institutional reports require mandatory minimum |
| Encode immediately in frozen `ResearchReport` schema | Out of scope; engines/models frozen; governance first |
| SEBI Mode only | Research Mode needs equal content rigor |

## India / Research Mode

Research Mode remains default. Recommendation Status / Recommendation header
slots use Research Mode terminology and feature flags (**CV-008**); they do not
authorize Buy/Sell labels when flags are off — show gated/honest status instead.
