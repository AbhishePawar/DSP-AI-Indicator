# Architecture Checklist

| Field | Value |
|---|---|
| **Status** | **MANDATORY** |
| **Last updated** | 2026-07-28 |
| **When** | Architecture review · before COMPLETE · before release |

A single **FAIL** on a required row fails architecture review.

---

## A. Tier-0 Core Values (CV-001…CV-010) — blocking

| ✓ | Check |
|---|---|
| | **CV-001** — No fabricated / placeholder production financial or market numbers |
| | **CV-002** — No score/valuation/recommendation on incomplete mandatory sources; else **Data unavailable.** |
| | **CV-003** — Scores/recommendations expose Source · Formula · Inputs · Weights · Engine · Confidence · Reasoning · Contribution |
| | **CV-004** — Deterministic / reproducible; no hidden AI re-scoring |
| | **CV-005** — Uncertainty stated; prefer **Unable to calculate.** over fake certainty |
| | **CV-006** — Full traceability chain present |
| | **CV-007** — Audit envelope fields present or honestly unavailable |
| | **CV-008** — Research before recommendation; Research Mode / flags honored |
| | **CV-009** — No bypass of architecture / compliance / governance / audit / security / core values |
| | **CV-010** — Quality preferred over speed/convenience/novelty |
| | [CORE_VALUES.md](CORE_VALUES.md) / [ARCHITECTURE_BIBLE.md](ARCHITECTURE_BIBLE.md) acknowledged |

---

## B. Research Standards (RS-001…RS-010) — blocking for reports

| ✓ | Check |
|---|---|
| | **RS-001** Executive Summary present |
| | **RS-002** Authenticated market data fields (or Data unavailable.) |
| | **RS-003** Financial statement analysis minimum |
| | **RS-004** Valuation block with authenticated inputs |
| | **RS-005** Margin of Safety prominent near top — never hidden |
| | **RS-006** Business Quality minimum |
| | **RS-007** Risk Analysis mandatory |
| | **RS-008** Scenario Analysis (bull/base/bear) |
| | **RS-009** Explainability for every score |
| | **RS-010** Audit & provenance complete |
| | Mandatory header displayed first |
| | [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md) acknowledged |

---

## C. Report / research authenticity

| ✓ | Check |
|---|---|
| | Metric provenance present |
| | Financial fields are **reported**, **calculated**, or **unavailable** — no guessed numbers ([derivation policy](FINANCIAL_DATA_DERIVATION_POLICY.md)) |
| | Research report validation includes **CV-001…CV-010** and **RS-001…RS-010** |
| | Emitter validation planned/implemented for new report generators |

---

## D. Platform invariants

| ✓ | Check |
|---|---|
| | Thin client — no browser investment math |
| | No unauthorized `/api/v1` contract change |
| | No unauthorized engine / scoring / model / boundary change |
| | Dependency / hexagonal boundaries respected |

---

## E. Governance

| ✓ | Check |
|---|---|
| | [ARCHITECTURE_GOVERNANCE.md](ARCHITECTURE_GOVERNANCE.md) freeze rules followed |
| | ADR filed when architecture decision changed |
| | [IMPLEMENTATION_QUALITY_GATE.md](IMPLEMENTATION_QUALITY_GATE.md) satisfied |

**Any CV-001…CV-010 or RS-001…RS-010 violation (in scope) ⇒ Architecture review FAIL.**
