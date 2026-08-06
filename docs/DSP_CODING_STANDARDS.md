# DSP Coding Standards

| Field | Value |
|---|---|
| **Version** | `1.1.0` |
| **Status** | **Stable** |
| **Last updated** | 2026-07-23 |
| **Audience** | Contributors · AI agents |

## Purpose

**Canonical** architecture-facing coding rules and official **GREEN** definition. Style minutiae belong in linters. Dependency direction → [DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md) §Dependency rules (do not restate matrices here).

---

## 1. Global

| Rule | Detail |
|---|---|
| Scope discipline | One declared scope class; change only what the task requires |
| Protected modules | Obey [DSP_STATUS.md](DSP_STATUS.md) §Protected |
| No silent architecture edits | STOP → [DSP_DECISION_RECORDS.md](DSP_DECISION_RECORDS.md) |
| **CV-001 authenticity** | Never invent production financial/market numbers; show **Data unavailable.** · [CORE_VALUES.md](CORE_VALUES.md) |
| **Tier-0 CV-002…CV-010** | Source-before-score · explainability · determinism · transparency · traceability · audit · research-first · governance · quality-over-speed |
| Safety checklist | [DSP_AI_COLLABORATION.md](DSP_AI_COLLABORATION.md) before code |
| Secrets | Never commit keys |
| Naming | [DSP_GLOSSARY.md](DSP_GLOSSARY.md) |

---

## 2. Python domain (`packages/`)

1. Depend inward only; public façades only.  
2. Immutable value objects where established.  
3. Evidence / explanation on decision-influencing outputs.  
4. I/O via ports + adapters.  
5. Deterministic scoring; seed if randomness is ever required.  
6. No business logic in `api_platform` / `security_platform` / `production_platform`.

---

## 3. TypeScript web (`apps/web`)

1. No investment math (thin client).  
2. View-models map envelopes; components render.  
3. Research Mode helpers over hard-coded Buy/Sell.  
4. Unavailable honesty; no invented Street / IV.  
5. Label client-only persistence.  
6. WCAG AA targets; keyboard / focus / live regions.  
7. Lazy panels; avoid accidental heavy trees.

---

## 4. Immutability

Domain artifacts immutable after create · web state replaced not stealth-mutated · reports/saves use snapshots.

---

## 5. Explainability checklist (user-visible numbers)

Source/category · confidence or Insufficient Evidence · methodology/version · limitations or Unavailable · no unexplained scores.

Detail → [USER_TRUST_STANDARD.md](USER_TRUST_STANDARD.md).

---

## 6. Regression Policy — official meaning of **GREEN**

A change set is **GREEN** only when **all** applicable rows pass:

| Dimension | Pass criteria |
|---|---|
| **Build** | Relevant packages/apps compile/install without error |
| **Tests** | Targeted suite passes; after Python package edits run `pytest --import-mode=importlib` (full regression when engines/API touched) |
| **Architecture** | Ownership, dependency rules, thin-client invariants hold; no new cycles; **Tier-0 CV-001…CV-010** |
| **Public APIs** | `/api/v1` and public façades remain backward compatible unless epic/RC explicitly breaks |
| **Deterministic outputs** | Same engine inputs → same outputs; presentation remaps labels only |
| **Documentation** | Docs task: suite consistent; code task: freeze/status/changelog updated when release-facing |

If any applicable dimension fails → **not GREEN**. Do not claim COMPLETE.

Quality gate narrative → [IMPLEMENTATION_QUALITY_GATE.md](IMPLEMENTATION_QUALITY_GATE.md).  
Authenticity → [CV_001_DATA_AUTHENTICITY_FIRST.md](CV_001_DATA_AUTHENTICITY_FIRST.md) · Tier-0 → [CV_002_TO_010_TIER0_CORE_VALUES.md](CV_002_TO_010_TIER0_CORE_VALUES.md) · Research Standards → [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md) · [CODE_REVIEW_CHECKLIST.md](CODE_REVIEW_CHECKLIST.md).

---

## 7. Definition of done

GREEN (§6) + Quality Gate + **Tier-0 CV-001…CV-010** + **RS-001…RS-010** (reports) + sprint DO NOT MODIFY honored.

---

## 8. Related

[DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md) · [DSP_AI_COLLABORATION.md](DSP_AI_COLLABORATION.md) · [DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md) · [CONTRIBUTING.md](CONTRIBUTING.md) · [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
