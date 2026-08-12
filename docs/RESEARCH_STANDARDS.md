# Research Standards

| Field | Value |
|---|---|
| **Status** | **MANDATORY · Constitutional** |
| **Last updated** | 2026-07-28 |
| **Catalog** | [RS_001_TO_RS_010.md](RS_001_TO_RS_010.md) |
| **ADR** | [adr/ADR-RS-001-research-standards.md](adr/ADR-RS-001-research-standards.md) |

---

## Purpose

Define the **minimum required content** of every DSP AI Indicator production
research report.

| Layer | Governs |
|---|---|
| **Core Values (CV-001…CV-010)** | *How* the platform behaves |
| **Research Standards (RS-001…RS-010)** | *What* every report must contain |

Both are constitutional. **RS violation MUST FAIL Research Report Validation**
and fails Architecture Review / Code Review / DoD / Release / Production /
Package Health when report surfaces are in scope.

---

## Register

| ID | Name |
|---|---|
| **RS-001** | Executive Summary |
| **RS-002** | Authenticated Market Data |
| **RS-003** | Financial Statement Analysis |
| **RS-004** | Valuation |
| **RS-005** | Margin of Safety |
| **RS-006** | Business Quality |
| **RS-007** | Risk Analysis |
| **RS-008** | Scenario Analysis |
| **RS-009** | Explainability |
| **RS-010** | Audit & Provenance |

Full field lists → [RS_001_TO_RS_010.md](RS_001_TO_RS_010.md).

---

## Mandatory header (first)

Current Market Price · Intrinsic Value · Margin of Safety · Fair Value Range ·
Expected CAGR · Confidence · Overall Score · Research Status · Recommendation

---

## Alignment with Core Values

| RS | Primary CV |
|---|---|
| RS-002 | CV-001 · CV-002 |
| RS-004 | CV-002 · CV-004 |
| RS-005 | CV-001 · CV-003 |
| RS-009 | CV-003 · CV-006 |
| RS-010 | CV-006 · CV-007 |
| All | CV-008 research-first · CV-009 governance · CV-010 quality |

Unavailable authenticated data → **Data unavailable.**  
Unable to compute → **Unable to calculate.**  
Never fabricate to satisfy an RS field.

---

## Enforcement

| Gate | Effect of RS violation |
|---|---|
| Research Report Validation | **FAIL** |
| Architecture Review | **FAIL** |
| Code Review | Block merge (report/emitter work) |
| Definition of Done | Incomplete |
| Quality Gate | Incomplete |
| Release / Production | **FAIL** |
| Package Health | **FAIL** when report packages touched |

---

## Non-goals

Does **not** modify engines, scoring, APIs, models, package boundaries,
deterministic behaviour, or business logic. Governance and documentation only
until a dedicated report-emitter epic implements validation.

---

## Related

[ARCHITECTURE_BIBLE.md](ARCHITECTURE_BIBLE.md) · [CORE_VALUES.md](CORE_VALUES.md) ·
[REPORT_ARCHITECTURE.md](REPORT_ARCHITECTURE.md) ·
[RESEARCH_REPORT_SPECIFICATION.md](RESEARCH_REPORT_SPECIFICATION.md) ·
[RESEARCH_ARCHITECTURE.md](RESEARCH_ARCHITECTURE.md)
