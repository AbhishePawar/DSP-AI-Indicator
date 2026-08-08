# Research Report Specification

| Field | Value |
|---|---|
| **Status** | **MANDATORY (governance)** |
| **Last updated** | 2026-07-28 |
| **Authority** | [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md) · [RS_001_TO_RS_010.md](RS_001_TO_RS_010.md) · [REPORT_ARCHITECTURE.md](REPORT_ARCHITECTURE.md) · [CORE_VALUES.md](CORE_VALUES.md) |
| **Implementation note** | Spec for **emitters / future generators**; does not alter frozen engine math or schemas in this governance update |

---

## 0. Research Standards (RS-001…RS-010)

Every production research report **MUST** satisfy [RS_001_TO_RS_010.md](RS_001_TO_RS_010.md).

| ID | Section |
|---|---|
| RS-001 | Executive Summary |
| RS-002 | Authenticated Market Data |
| RS-003 | Financial Statement Analysis |
| RS-004 | Valuation |
| RS-005 | Margin of Safety (prominent) |
| RS-006 | Business Quality |
| RS-007 | Risk Analysis |
| RS-008 | Scenario Analysis |
| RS-009 | Explainability |
| RS-010 | Audit & Provenance |

**Missing section = Research Report Validation FAIL.**

---

## 1. Mandatory header (display first)

| Field | Required | If missing |
|---|---|---|
| Current Market Price | Yes | **Data unavailable.** |
| Intrinsic Value | Yes | **Data unavailable.** / **Unable to calculate.** |
| Margin of Safety | Yes | **Data unavailable.** / **Unable to calculate.** |
| Fair Value Range | Yes | **Data unavailable.** / **Unable to calculate.** |
| Expected CAGR | Yes (slot) | **Data unavailable.** when not computed |
| Confidence | Yes | **Data unavailable.** |
| Overall Score | Yes | **Data unavailable.** / **Unable to calculate.** |
| Research Status | Yes | Honest status label |
| Recommendation | Yes | Research Mode–gated status — never invent advice labels |

---

## 2. Metric object (internal contract)

Each metric object **SHALL** include:

```text
value            → number | null (null ⇒ present as "Data unavailable.")
source           → market | financial_statement | dsp_calculated | user_input | derived
timestamp        → ISO-8601 / aware datetime
reporting_period → string | null
calculation_engine → string | null
version          → string | null
confidence       → level | null
```

Null `value` with invented display text is a **CV-001 / RS** violation.

---

## 3. Score explainability (RS-009 · CV-003)

| Element | Required |
|---|---|
| Formula | Yes |
| Raw inputs | Yes |
| Weights | Yes (when weighted) |
| Calculation | Yes |
| Contributing Engines | Yes |
| Confidence | Yes (when applicable) |
| Supporting Data | Yes |
| Reasoning | Yes |
| Source Data | Yes |
| Contribution | Yes (when multi-factor) |

---

## 4. Forbidden content

Placeholder masks, dummy %, invented market data (**RS-002**), valuation without
authenticated inputs (**RS-004**), hidden Margin of Safety (**RS-005**),
black-box scores (**RS-009**), and missing audit provenance (**RS-010**) are
**forbidden**.

---

## 5. Validation gate

Emitters **MUST** refuse production emit when any **RS-001…RS-010** or
**CV-001…CV-010** check fails.

### Audit envelope (RS-010 · CV-007)

Report ID · Audit Reference · Generation Timestamp · Engine Version ·
Rules Version · Data Timestamp · Financial Statement Period · Source Metadata ·
Calculation Metadata · Research Version.

---

## 6. Compatibility

Existing `ResearchReport` domain models remain valid presentation assemblies
([F1_3_RESEARCH_REPORTER.md](F1_3_RESEARCH_REPORTER.md)). This specification
**adds** constitutional content requirements for production-facing research
reports; it does not rewrite frozen schemas in this governance update.

Frontend canonical RS implementation →
[DASHBOARD_ARCHITECTURE.md](DASHBOARD_ARCHITECTURE.md) (`/research/institutional`).
