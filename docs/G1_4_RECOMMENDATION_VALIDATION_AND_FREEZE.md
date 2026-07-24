# Phase G1.4 — Recommendation Validation & Architecture Freeze

**Status:** **FROZEN** · Validation / documentation only · **No package or business-logic changes in this phase**

**Baseline:** `packages/recommendation/` **0.4.0** (G1.0–G1.3)  
**Suite gate:** **1328 / 1328** passing · **62 / 62** `recommendation` tests (2026-07-21)

This phase validates and freezes the **Recommendation Intelligence** subsystem
as the platform’s independent **decision synthesis** bounded context — a
cite-only consumer of frozen qualitative and quantitative outputs.

It does **not** implement optimization, OMS, trading, workflow, LLM reasoning,
ML ranking, or preference engines.

Authoritative prior freezes:

- [G0.0A Architecture Freeze](G0_0A_RECOMMENDATION_ARCHITECTURE_FREEZE.md)
- Implemented surface: [G1.0](G1_0_RECOMMENDATION_DOMAIN_MODELS.md) ·
  [G1.1](G1_1_RECOMMENDATION_ASSEMBLER.md) ·
  [G1.2](G1_2_RECOMMENDATION_ENGINE.md) ·
  [G1.3](G1_3_RECOMMENDATION_REPORTER.md)

On conflicts about ownership / dependencies / pipeline / explainability,
**G0.0A + this document** win. This document freezes the **implemented** G1
surface at `0.4.0`.

---

## 1. Validation results

| # | Area | Result | Notes |
|---|---|---|---|
| 1 | Architecture | **PASS** | Models → Assembler → Engine → Reporter → `RecommendationReport` |
| 2 | Domain ownership | **PASS** | Owns Identity / Profile / Option / Score / Rationale / Conflict / Summary / Report only |
| 3 | Dependency graph | **PASS** | Domain runtime deps = `{core}`; local refs; no reverse imports / cycles |
| 4 | Domain model contracts | **PASS** | Immutable frozen dataclasses; option + score contracts complete |
| 5 | Assembler responsibilities | **PASS** | Citation construction / validation only; empty content skeleton |
| 6 | Engine responsibilities | **PASS** | Deterministic baseline synthesis; cite-backed; no primary analysis |
| 7 | Reporter responsibilities | **PASS** | Presentation only; preserves Decimals / ordering / citations |
| 8 | Confidence policy | **PASS** | Agreement / conflict / coverage / consistency — not market prediction |
| 9 | Explainability policy | **PASS** | Rationales restate postures + conflicts + citations; no hidden reasoning |
| 10 | Citation & provenance | **PASS** | Opaque `kind:id` keys; scores require provenance / method_id / unit |
| 11 | Validation rules | **PASS** | Duplicates, broken refs, missing required upstream citations, orphan conflicts |
| 12 | Extension model | **PASS** | Additive preferences / suitability / tax / multi-strategy — no redesign |

**Overall:** **PASS**

---

## 2. Architecture validation

### Canonical pipeline (frozen)

```text
Immutable Domain Models (G1.0)
        │
        ▼
Recommendation Assembler (G1.1)
  · Decision / Comparison / Portfolio / Risk / Research / Quant refs
        │
        ▼
Recommendation Engine (G1.2)
  · baseline rules + caller-declared SignalPosture overlays
        │
        ▼
Recommendation Reporter (G1.3)
        │
        ▼
RecommendationReport  (canonical immutable presentation)
```

**Confirmed absent from this freeze surface:**

- Primary analysis engines (DI / IEF / Comparison / Risk / Research / Quant)  
- Portfolio optimization / OMS / trading / execution  
- Workflow / LLM / ML ranking inside the domain  
- Mandatory charts / persistence  

**Legacy note (frozen coexistence):** Sprint 7.1 `RecommendationMapper`
(committee → `contracts.Recommendation`) remains a **non-domain adapter**
export. It is **not** the Recommendation Intelligence engine and must not be
treated as G pipeline synthesis.

---

## 3. Ownership validation

| Domain | Owns | Recommendation relationship |
|---|---|---|
| Decision / IEF / Comparison / Portfolio / Risk / Research / Quant | Frozen reports / engines | Cited only via local refs |
| **Recommendation Intelligence** | See list below | Aggregate owner of action-synthesis artifacts |
| Optimizer / OMS / Workflow / Copilot (future) | Search / execution / process / UX | Consume `RecommendationReport` externally |

### Recommendation owns ONLY

| Artifact | Role |
|---|---|
| `RecommendationIdentity` | Session identity |
| `RecommendationProfile` | Aggregate root |
| `RecommendationOption` | Action posture candidate |
| `RecommendationScore` | Transparent confidence (Decimal) |
| `RecommendationRationale` | Cite-backed explanation |
| `RecommendationConflict` | Declared tension |
| `RecommendationSummary` | Counts / limitations |
| `RecommendationReport` | Canonical immutable presentation |

Supporting (not upstream ownership): local refs, Assembler / Engine / Reporter
context·result·status types, `SignalPosture` overlays.

### Recommendation owns NONE of

`DecisionPack` · `EvidenceBundle` · `ComparisonReport` · `Portfolio` ·
qualitative / quantitative risk engines · Research engines · Execution ·
Trading · Optimization · OMS · Workflow.

**No ownership leakage detected.**

---

## 4. Dependency validation

```text
                    ┌─────────────┐
                    │ dsp_platform │  (composition root — re-exports)
                    └──────┬──────┘
                           │ imports
                           ▼
                 ┌──────────────────┐
                 │  recommendation  │  ← FROZEN domain (0.4.0)
                 │  models/assembler│
                 │  engine/reporter │
                 └────────┬─────────┘
                          │
                          ▼
                       ┌──────┐
                       │ core │
                       └──────┘

Upstream DI / Comparison / Portfolio / Risk / Research / Quant
are cited via local reference types only — not imported by domain modules.

Legacy mapper.py may import contracts / ai_committee (adapter only).
```

| Claim | Status |
|---|---|
| Domain module deps ⊆ `{core}` (+ package-local) | **Confirmed** |
| `pyproject.toml` dependencies = `["core"]` | **Confirmed** |
| Reference-only upstream consumption | **Confirmed** |
| No reverse imports into frozen upstream domains | **Confirmed** (architecture tests) |
| No cycles / no engine-to-engine coupling | **Confirmed** |
| No vendor SDKs in domain modules | **Confirmed** |

**Forbidden in domain modules (confirmed absent):**

`portfolio`, `risk`, `research`, `quantitative_risk`, `decision_intelligence`,
`comparison`, `industry`, `data_engine`, `dsp_platform`, vendor/broker SDKs.

---

## 5. Assembler validation

| Rule | Status |
|---|---|
| Requires Decision / Comparison / Portfolio / Risk / Research / Quant refs | **PASS** |
| Emits empty options / scores / rationales / conflicts | **PASS** |
| No synthesis / scoring / mapper dependency | **PASS** |
| Duplicate / broken / foreign-ownership checks | **PASS** |

APIs frozen: `RecommendationAssembler`, `AssemblyContext`, `AssemblyResult`,
`AssemblyStatus`.

---

## 6. Engine validation

| Rule | Status |
|---|---|
| Deterministic baseline (`…baseline_rules.v1`) | **PASS** |
| Consumes `AssemblyResult` + declared `SignalPosture` only | **PASS** |
| Explain-first rationales (postures + conflicts + citations) | **PASS** |
| Evidence-backed options (citations mandatory) | **PASS** |
| No hidden reasoning / primary analysis / market prediction | **PASS** |
| Explicit `RecommendationConflict` objects | **PASS** |
| Confidence ≠ market forecast | **PASS** |

APIs frozen: `RecommendationEngine`, `EngineContext`, `EngineResult`,
`EngineStatus`, `SignalPosture`.

### Confidence policy (frozen)

Reflects evidence agreement, conflict severity, coverage completeness, and
consistency. Decimal levels: LOW `0.35` · MEDIUM `0.55` · HIGH `0.75` ·
VERY_HIGH `0.90`. Score never replaces rationale.

### Explainability policy (frozen)

1. Every option cites supporting report keys and rationale ids.  
2. Rationale body enumerates postures and conflict titles.  
3. Conflicts are first-class objects with severity + refs.  
4. Method id is mandatory on scores.  
5. No opaque ML / LLM path in the frozen baseline.

---

## 7. Reporter validation

| Rule | Status |
|---|---|
| Consumes `RecommendationReport` / `EngineResult` only | **PASS** |
| No engine execution / no upstream report access | **PASS** |
| Preserves option ordering and Decimal identity | **PASS** |
| Preserves citations / provenance | **PASS** |
| Never recalculates confidence or invents options | **PASS** |
| Preferred vs alternate split is presentational | **PASS** |

APIs frozen: `RecommendationReporter`, `ReportingContext`, `ReportingResult`,
`ReportingStatus`, `ReportMetadata`, `CitationSection`.

---

## 8. Domain contracts (frozen)

**Option:** `option_id`, `option_type`, `title`, `description`,
`supporting_rationale_refs`, `supporting_report_refs`, `confidence_reference`,
`priority`.

**Score:** `score_id`, `score_type`, Decimal `value`, `unit`, `method_id`,
non-empty `provenance`, `calculation_timestamp` (+ optional `confidence_level`).

Enums frozen: `RecommendationType`, `ConflictSeverity`, `ConfidenceLevel`,
`AssemblyStatus`, `EngineStatus`, `ReportingStatus`, `SignalPosture`.

---

## 9. Extension model (frozen)

Future work remains **additive** — no redesign of ownership, pipeline, or
explainability:

| Extension | Pattern |
|---|---|
| Advisor preferences | Additive policy inputs / method ids |
| Client suitability | Additive constraints / limitation notes |
| Tax-aware recommendations | Additive option annotations / methods |
| Multi-strategy / scenario recommendations | Additive options / conflicts |
| Personalized recommendation policies | Plug-in methods outside frozen baseline |
| Optimizer / OMS / Workflow | External consumers of `RecommendationReport` |

**Forbidden redesigns:** absorbing DI/Risk/Research/Quant engines; making
Assembler optional removal of cite-only rule; float public scores; hidden
LLM-required synthesis in domain core.

---

## 10. Known technical debt (document only)

1. **Caller-declared `SignalPosture` overlays** — baseline does not derive
   postures from upstream report payloads; richer derivation is additive.  
2. **Advanced confidence calibration** — fixed Decimal bands; no empirical
   calibration layer.  
3. **Policy plug-ins / preference engines** — not implemented.  
4. **Multi-objective ranking** — preferred + alternate only; no Pareto search.  
5. **Advisor workflows / approvals** — belong to Epic H, not this package.  
6. **Legacy `RecommendationMapper` coexistence** — committee wire adapter still
   exported beside the G domain; long-term packaging clarity optional.  
7. **EvidenceBundle citation** — not a required Assembler input in G1.1
   (Decision / Comparison / Portfolio / Risk / Research / Quant required).  
8. **No tax / suitability / multi-account policies** in baseline.

---

## 11. Future roadmap

| Phase / Epic | Scope | Status |
|---|---|---|
| G0.0 / G0.0A | Design + architecture freeze | **DONE / FROZEN** |
| G1.0 | Domain models | **DONE / FROZEN** |
| G1.1 | Assembler | **DONE / FROZEN** |
| G1.2 | Engine | **DONE / FROZEN** |
| G1.3 | Reporter | **DONE / FROZEN** |
| **G1.4** | Validation & freeze (this document) | **DONE / FROZEN** |
| Additive G increments | Preferences / suitability / tax / scenarios | Planned |
| Epic H Workflow | Approvals / investigation steps | Future |
| Optimizer / OMS | Search / execution consumers | Future |

---

## 12. Freeze confirmation

**CONFIRMED.**

Recommendation Intelligence — architecture, ownership, dependencies,
Assembler / Engine / Reporter responsibilities, confidence & explainability
policies, citation / provenance guarantees, and additive extension model —
is **fully validated and architecturally frozen** at package `0.4.0`.

It is ready to serve as the platform’s canonical **decision synthesis**
subsystem for downstream Workflow / Optimizer / OMS / UI consumers, subject
to the technical-debt conditions below.

Qualitative stack, Quantitative Risk, Portfolio, and Baseline v1.0 freezes
remain untouched.

---

## 13. PASS / FAIL

**PASS** — Recommendation Intelligence is validated and frozen.

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | **Authoritative Recommendation (G1) validation & freeze** |
| [G0_0A_RECOMMENDATION_ARCHITECTURE_FREEZE.md](G0_0A_RECOMMENDATION_ARCHITECTURE_FREEZE.md) | Architecture freeze |
| [G0_0_RECOMMENDATION_INTELLIGENCE_DESIGN.md](G0_0_RECOMMENDATION_INTELLIGENCE_DESIGN.md) | Design (historical on conflicts) |
| [G1_0_RECOMMENDATION_DOMAIN_MODELS.md](G1_0_RECOMMENDATION_DOMAIN_MODELS.md) | Models |
| [G1_1_RECOMMENDATION_ASSEMBLER.md](G1_1_RECOMMENDATION_ASSEMBLER.md) | Assembler |
| [G1_2_RECOMMENDATION_ENGINE.md](G1_2_RECOMMENDATION_ENGINE.md) | Engine |
| [G1_3_RECOMMENDATION_REPORTER.md](G1_3_RECOMMENDATION_REPORTER.md) | Reporter |
| [E2_4_QUANTITATIVE_RISK_VALIDATION_AND_FREEZE.md](E2_4_QUANTITATIVE_RISK_VALIDATION_AND_FREEZE.md) | Quant upstream freeze |
| [F1_4_RESEARCH_VALIDATION_AND_FREEZE.md](F1_4_RESEARCH_VALIDATION_AND_FREEZE.md) | Research upstream freeze |
| [DSP_ARCHITECTURE_BASELINE_v1_0.md](DSP_ARCHITECTURE_BASELINE_v1_0.md) | Platform baseline |

---

## Final question

Is Recommendation Intelligence fully validated, architecturally frozen, and
ready to serve as the platform's canonical decision synthesis subsystem?

**YES WITH CONDITIONS**
