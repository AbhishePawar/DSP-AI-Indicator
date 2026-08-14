# Report Architecture

| Field | Value |
|---|---|
| **Status** | **MANDATORY (governance)** |
| **Last updated** | 2026-07-28 |
| **Implements** | [CV_001_DATA_AUTHENTICITY_FIRST.md](CV_001_DATA_AUTHENTICITY_FIRST.md) · [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md) |
| **Companion** | [RESEARCH_REPORT_SPECIFICATION.md](RESEARCH_REPORT_SPECIFICATION.md) · [RS_001_TO_RS_010.md](RS_001_TO_RS_010.md) · [F1_3_RESEARCH_REPORTER.md](F1_3_RESEARCH_REPORTER.md) |

---

## Purpose

Define architecture rules for **research report presentation** without changing
frozen engines, scoring, or `/api/v1` contracts.

Reporters **assemble and present** authenticated artifacts. They must not invent
numbers.

---

## CV-001…CV-010 constraints on reports

1. No fabricated / placeholder financial or market numbers (**CV-001**).  
2. Missing mandatory inputs → **Data unavailable.**; never score incomplete mandatory sets (**CV-002**).  
3. Scores/recommendations explainable (**CV-003**).  
4. Deterministic / reproducible (**CV-004**); audit envelope (**CV-007**).  
5. Uncertainty honest — prefer **Unable to calculate.** (**CV-005**).  
6. Full provenance chain (**CV-006**).  
7. Research before recommendation framing (**CV-008**).  
8. No governance bypass in emitters (**CV-009**); quality over speed (**CV-010**).

---

## Mandatory header (every research report)

Per [RS_001_TO_RS_010.md](RS_001_TO_RS_010.md) — display **first**:

| Field | Source rule |
|---|---|
| Current Market Price | Market Data only — else **Data unavailable.** |
| Intrinsic Value | DSP AI Calculated — else unavailable / unable to calculate |
| Margin of Safety | DSP AI Calculated — **prominent**; never hide (**RS-005**) |
| Fair Value Range | DSP AI Calculated — else unavailable |
| Expected CAGR | Calculated/derived if available — else unavailable |
| Confidence | Engine / pack confidence — else unavailable |
| Overall Score | DSP AI Calculated — else unavailable |
| Research Status | Honest status |
| Recommendation | Research Mode–gated status |

---

## Research Standards (RS-001…RS-010)

Minimum sections: Executive Summary · Authenticated Market Data · Financial
Statements · Valuation · Margin of Safety · Business Quality · Risk · Scenarios ·
Explainability · Audit & Provenance.

**Missing section = FAIL** Research Report Validation.

---

## Emitter validation (future generators MUST)

Before emitting a production research report:

| ✓ | Validation |
|---|---|
| | No placeholder / fabricated market or statement numbers (**CV-001**) |
| | Mandatory sources validated before scores (**CV-002**) |
| | Explainability fields present (**CV-003**) |
| | Reproducible / deterministic path (**CV-004**) |
| | Uncertainty / Unable to calculate honest (**CV-005**) |
| | Provenance chain complete (**CV-006**) |
| | Audit envelope present (**CV-007**) |
| | Research-before-recommendation framing (**CV-008**) |
| | **RS-001…RS-010** all sections present (or validation FAIL) |

---

## Layering

```text
Authenticated inputs (market / statements / user)
        → deterministic engines (unchanged)
        → research synthesis / packs
        → ResearchReporter / report emitters  ← CV-001 gate
        → thin client presentation
```

---

## Non-goals

- Changing valuation / quality / recommendation engines  
- Changing API envelopes  
- Adding business features  
