# CV-002 … CV-010 — Tier-0 Core Values

| Field | Value |
|---|---|
| **Status** | **MANDATORY · Tier-0 Architecture Governance** |
| **Effective** | 2026-07-28 |
| **Violation class** | **Architecture Violation** |
| **Authority** | [CORE_VALUES.md](CORE_VALUES.md) · [ARCHITECTURE_BIBLE.md](ARCHITECTURE_BIBLE.md) · [adr/ADR-CV-002-010-tier0-core-values.md](adr/ADR-CV-002-010-tier0-core-values.md) |
| **Companion** | [CV_001_DATA_AUTHENTICITY_FIRST.md](CV_001_DATA_AUTHENTICITY_FIRST.md) |

These values are **Constitutional**. Convenience, demo pressure, and speed
**never** waive them. Violation **MUST FAIL** architecture review and all
listed quality gates.

**This document is governance only.** It does not change engines, scoring,
APIs, models, deterministic behaviour, or package boundaries.

---

## CV-002 — Source Before Score

No valuation, score, ranking, intrinsic value, recommendation, or AI output
may be **produced for production research presentation** until all
**mandatory** source data for that output has been successfully validated.

| If mandatory inputs are missing | Rule |
|---|---|
| Display | **Data unavailable.** |
| Calculate | **Never** calculate using incomplete mandatory inputs |

Downstream presentation must not invent a score to fill the UI.

---

## CV-003 — Explainability Before Recommendation

Every score and recommendation **MUST** be explainable.

Every user-visible scored / recommended output **SHALL** expose (or link to):

| Element |
|---|
| Source Data |
| Formula |
| Inputs |
| Weights |
| Engine |
| Confidence |
| Reasoning |
| Contribution |

**No black-box outputs.**

---

## CV-004 — Determinism Before Intelligence

Given identical authenticated inputs:

| Requirement | Rule |
|---|---|
| Outputs | Identical |
| Randomness | Forbidden in production research scoring / ranking |
| Hidden AI adjustments | Forbidden — AI must not silently mutate deterministic results |
| Reports | Every report **MUST** be reproducible |

AI may explain; it must not secretly re-score.

---

## CV-005 — Transparency Over Confidence

If uncertainty exists: **state uncertainty**. Never fabricate certainty.

Prefer:

> **Unable to calculate.**

over guessed or soft-estimated values when mandatory confidence cannot be
established. Aligns with CV-001 (no invented numbers) and Trust Standard
honesty categories.

---

## CV-006 — Traceability By Design

Every output **SHALL** be traceable through:

```text
Output
  → Engine
  → Formula
  → Input
  → Source
  → Timestamp
  → Version
```

Complete provenance required for production research artifacts.

---

## CV-007 — Auditability First

Every research report **SHALL** be reproducible for audit.

Required audit envelope (present or explicitly unavailable — never invented):

| Field |
|---|
| Configuration |
| Engine Version |
| Rule Version |
| Input Data (reference / digest) |
| Calculation Version |
| Timestamp |
| Audit Reference |

---

## CV-008 — Research Before Recommendation

DSP AI Indicator exists to generate **research**.

Recommendations are **downstream** research outputs. Research always comes
first. Research Mode terminology and feature flags remain mandatory; advice
labels stay gated.

---

## CV-009 — Governance Over Convenience

No feature may bypass:

| Gate |
|---|
| Architecture |
| Compliance |
| Governance |
| Audit |
| Security |
| Core Values (CV-001…CV-010) |

**Convenience never overrides governance.**

---

## CV-010 — Quality Over Speed

Always prefer:

| Prefer | Over |
|---|---|
| Correctness | Speed |
| Authenticity | Convenience |
| Explainability | Complexity |
| Reproducibility | Novelty |
| Verified Data | Fast Data |

---

## Enforcement (all gates)

Architecture Review · Code Review · Definition of Done · Quality Gates ·
Release · Production · Package Health · Research Report Validation

**Any CV-002…CV-010 violation = FAIL.**

See [ARCHITECTURE_CHECKLIST.md](ARCHITECTURE_CHECKLIST.md) ·
[CODE_REVIEW_CHECKLIST.md](CODE_REVIEW_CHECKLIST.md) ·
[IMPLEMENTATION_QUALITY_GATE.md](IMPLEMENTATION_QUALITY_GATE.md).
