# Code Review Checklist

| Field | Value |
|---|---|
| **Status** | **MANDATORY** |
| **Last updated** | 2026-07-28 |

Reviewers **must** block merge on **any** CV-001…CV-010 violation, and on
**RS-001…RS-010** violations for research report / emitter changes.

---

## Tier-0 Core Values — blocking

| ✓ | Check |
|---|---|
| | **CV-001** — No invented / placeholder production numbers |
| | **CV-002** — No calculation path on incomplete mandatory inputs |
| | **CV-003** — Explainability surface present for scores/recommendations |
| | **CV-004** — No randomness / hidden AI adjustment of deterministic results |
| | **CV-005** — Uncertainty / Unable to calculate used honestly |
| | **CV-006** — Provenance / traceability not stripped |
| | **CV-007** — Audit fields preserved on research reports where applicable |
| | **CV-008** — No recommendation-first UI that skips research context |
| | **CV-009** — No “temporary” bypass of governance / compliance / security |
| | **CV-010** — No shortcut that trades authenticity/correctness for speed |

---

## Research Standards (RS) — blocking for report work

| ✓ | Check |
|---|---|
| | **RS-001…RS-010** sections present / validated |
| | Mandatory header first; MoS prominent (**RS-005**) |
| | No estimated/placeholder market data (**RS-002**) |
| | Explainability + audit provenance (**RS-009**, **RS-010**) |
| | [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md) followed |

---

## Architecture

| ✓ | Check |
|---|---|
| | Thin client preserved |
| | No illegal package imports / deep engine imports from apps |
| | No silent API contract break |
| | Frozen engines / scoring / models / boundaries untouched unless epic unlocks them |

---

## Trust & quality

| ✓ | Check |
|---|---|
| | Traceable / explainable / honest labels |
| | Research Mode terminology |
| | Tests cover unavailable / unable-to-calculate paths where relevant |
| | Docs updated if governance surface changed |

Standards → [DSP_CODING_STANDARDS.md](DSP_CODING_STANDARDS.md) · [CONTRIBUTING.md](CONTRIBUTING.md) · [CORE_VALUES.md](CORE_VALUES.md)
