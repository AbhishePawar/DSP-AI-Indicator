# DSP Architecture Baseline v1.0

**Status:** **AUTHORITATIVE** · Documentation only  
**Phase:** P1.0 — DSP Architecture Baseline v1.0  
**Date:** 2026-07-21  
**Suite gate:** **1242 / 1242** passing  

This document is the **canonical architectural reference** for all future DSP
AI Indicator development. It freezes the qualitative platform stack through
Research Intelligence.

**Conflicts:** Subsystem freezes remain authoritative for their domain details.
This baseline wins on **platform-wide** ownership order, dependency direction,
lifecycle pattern, and extension rules. Subsystem freezes win on domain-local
contracts.

| Precedence | Documents |
|---|---|
| Platform (this file) | Stack order · cross-domain ownership · extension epics |
| Subsystem freezes | Domain models · component contracts · local invariants |

---

## 1. System overview

DSP AI Indicator is a layered qualitative intelligence platform. Each layer
**consumes** frozen outputs from layers below via **citations / references**
and **never owns** upstream aggregates.

```text
Analysis Framework
        ↓
Decision Intelligence
        ↓
Industry Evidence Framework
        ↓
Comparison
        ↓
Portfolio Intelligence
        ↓
Qualitative Risk Intelligence
        ↓
Research Intelligence          ← highest qualitative subsystem
```

| Layer | Answers (one-liner) |
|---|---|
| **Analysis Framework** | What do domain engines observe? |
| **Decision Intelligence** | Should I own it? (single name) |
| **Industry Evidence** | What evidence applies, and how is it assembled? |
| **Comparison** | How do peers compare under methodology? |
| **Portfolio** | What is owned, constrained, and changed? |
| **Risk (qualitative)** | What is the qualitative implication / posture? |
| **Research** | What should be investigated next? |

**Research Intelligence** is the terminal qualitative orchestration layer.
Future epics (E2 Quant, Recommendation, Workflow, Knowledge Graph, AI Copilot)
consume this stack additively — they do **not** redesign it.

### Composition root

`dsp_platform` is the composition / re-export root only. Domain packages must
**not** import `dsp_platform`. Applications and adapters may compose through it.

---

## 2. Subsystem ownership

### 2.1 Ownership matrix (platform)

| Subsystem | Owns | Consumes (cite / use) | Never owns |
|---|---|---|---|
| **Analysis Framework** | Domain analysis engines / signals / contracts surface for AIMF-style analysis | Market / fundamental / economic inputs via data paths | DecisionPack, Portfolio, Risk, Research |
| **Decision Intelligence** | `DecisionPack` and DI presentation / assurance artifacts | Analysis outputs; industry/methodology citations as designed | Evidence ownership, Comparison engine, Portfolio, Risk, Research |
| **Industry Evidence (IEF)** | Methodology, EvidenceBundle, providers, interpreters, applicability | Instrument / taxonomy context | DecisionPack, Comparison ownership, Portfolio, Risk, Research |
| **Comparison** | `ComparisonReport` and comparison engine artifacts | DecisionPack / Evidence citations | Portfolio, Risk, Research; Evidence reinterpretation as ownership |
| **Portfolio Intelligence** | Portfolio, holdings, constraints, snapshots, monitoring history, PortfolioReport | DecisionPack / Evidence / Comparison **references** | Risk artifacts, Research, engines, Evidence payloads |
| **Qualitative Risk** | RiskProfile, assessment, observations, descriptors, coverage, constraints, summary, RiskReport, IntegratedRiskContext | Portfolio / Monitoring / Decision / Evidence / Comparison **citations** | Portfolio, DecisionPack, Evidence, Comparison, Research, quant metrics (E1) |
| **Research Intelligence** | ResearchIdentity → ResearchReport (full research artifact set) | All upstream via **local references** | DecisionPack, EvidenceBundle, ComparisonReport, Portfolio, Monitoring, RiskProfile / RiskReport / IntegratedRiskContext, recommendations |

### 2.2 Research owns only (frozen list)

`ResearchIdentity` · `ResearchProfile` · `ResearchObservation` ·
`ResearchInsight` · `ResearchConflict` · `ResearchGap` · `ResearchAgenda` ·
`ResearchPriority` · `ResearchCoverage` · `ResearchSummary` · `ResearchReport`

### 2.3 Single-ownership rule

Every durable domain artifact has **exactly one** owning subsystem.
Consumers may cite digests / ids / reference objects. Consumers must not embed,
mutate, or re-home upstream aggregates.

---

## 3. Dependency graph

### 3.1 Canonical qualitative stack (logical)

```text
contracts / core
        ▲
        │
analysis engines / DI / IEF / comparison   (peer producers + shared kernel)
        ▲
        │  citations
portfolio  (frozen)
        ▲
        │  citations
risk       (frozen · qualitative E1)
        ▲
        │  citations (local refs in F1)
research   (frozen · terminal qualitative consumer)
        │
        ▼
dsp_platform   (re-exports only — composition root)
```

### 3.2 Rules (frozen)

1. **One-way dependencies** — lower layers never import higher layers.  
2. **No reverse imports** — Portfolio never imports Risk or Research; Risk never imports Research; DI / IEF / Comparison never import Portfolio / Risk / Research.  
3. **No cycles.**  
4. **No shared mutable ownership** — citations only; immutable contracts.  
5. **Research is the terminal qualitative consumer** — nothing qualitative above it in this baseline.  
6. Domain packages do not import `dsp_platform`.

### 3.3 Package baseline locations

| Subsystem | Package (canonical) |
|---|---|
| Shared kernel | `contracts`, `core` |
| Analysis / engines | `dsp`, `fundamental`, `economic`, `valuation`, … |
| Decision Intelligence | `decision_intelligence` |
| Industry Evidence | `industry` |
| Comparison | `comparison` |
| Portfolio | `portfolio` |
| Qualitative Risk | `risk` |
| Research | `research` |
| Composition | `dsp_platform` |

---

## 4. Implementation pattern

Every future subsystem **should** follow this canonical lifecycle:

```text
Design
  ↓
Architecture Freeze
  ↓
Hardening (optional)
  ↓
Domain Models
  ↓
Assembler
  ↓
Analyzer / Synthesizer
  ↓
Reporter
  ↓
Validation & Freeze
```

| Stage | Purpose |
|---|---|
| **Design** | Mission, ownership, non-goals |
| **Architecture Freeze** | Lock package, deps, contracts, responsibilities |
| **Hardening** | Invariants, claim language, traceability, guardrails |
| **Domain Models** | Immutable contracts only — no pipelines |
| **Assembler** | Construction from citations — no analysis |
| **Analyzer / Synthesizer** | Qualitative interpretation / synthesis — no upstream re-ownership |
| **Reporter** | Canonical immutable presentation — no new analysis |
| **Validation & Freeze** | Confirm ownership, deps, responsibilities; freeze version |

Optional additive stages (Integrator / Monitoring / platform exports) may appear
where a subsystem freeze explicitly allows them — never as a way to bypass
ownership rules.

---

## 5. Architectural principles

1. **Single ownership** — one owner per aggregate / report type.  
2. **Immutable contracts** — frozen dataclasses / snapshots; new events → new reports.  
3. **Reference-only upstream consumption** — cite digests / ids / refs; do not embed payloads.  
4. **Traceability** — synthesized artifacts preserve provenance (e.g. Insight → Observation → Evidence).  
5. **Claim-language policy** — forbid certainty / attractiveness / trade instruction vocabulary in domain text where subsystem policy applies.  
6. **No responsibility overlap** — Assembler ≠ Analyzer/Synthesizer ≠ Reporter.  
7. **No duplicated analysis** — never re-run upstream engines to “own” their conclusions.  
8. **No hidden coupling** — no reverse imports, no LLM/provider/persistence inside domain packages, no silent cross-domain mutation.

---

## 6. Guardrails

Explicitly **prohibited** across the qualitative baseline:

| Prohibition | Rationale |
|---|---|
| Reverse imports | Preserves one-way stack |
| Circular dependencies | Preserves freeze integrity |
| Cross-domain ownership | Single ownership rule |
| Portfolio mutation by Risk / Research | Portfolio owns structure / history |
| Risk mutation by Research | Risk owns posture artifacts |
| Evidence mutation by consumers | IEF owns Evidence |
| Recommendation inside Research | Research answers investigation, not action |
| Embedded LLM reasoning in domain | LLM adapters are app / extension layer |
| Persistence in domain packages | Infrastructure / memory services |
| Workflow orchestration in domain | Workflow epic / app layer |
| Agent execution in domain | Copilot / agent runtime |
| Trading / BUY·SELL·HOLD in qualitative domains | Recommendation / OMS |
| Optimization in qualitative domains | Optimizer epic / external |

---

## 7. Extension model

Future epics **consume** frozen qualitative outputs. They must **not** redesign
Analysis, DI, IEF, Comparison, Portfolio, qualitative Risk, or Research.

| Epic | Name | Pattern |
|---|---|---|
| **E2** | Quantitative Risk | Sibling / additive metrics train; cites Portfolio; separate freeze — **E2.0A + E2.4 FROZEN** · see [E2.4](E2_4_QUANTITATIVE_RISK_VALIDATION_AND_FREEZE.md) |
| **G** | Recommendation Intelligence | Consumes ResearchReport / RiskReport / QuantReport / Portfolio (+ DI/Comparison); emits `RecommendationReport` — **G0.0A + G1.4 FROZEN** · see [G1.4](G1_4_RECOMMENDATION_VALIDATION_AND_FREEZE.md) |
| **H** | Workflow Intelligence | Orchestrates investigation / approval / multi-subsystem lifecycle — **H1.4 FROZEN** · see [H1.4](H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md) · [H0.0A](H0_0A_WORKFLOW_INTELLIGENCE_ARCHITECTURE_FREEZE.md) |
| **I** | Knowledge Graph | Index / link citations; not a new owner of upstream aggregates — **I0.0A + I1.4 FROZEN** · see [I1.4](I1_4_KNOWLEDGE_GRAPH_VALIDATION_AND_FREEZE.md) · [I0.0A](I0_0A_KNOWLEDGE_GRAPH_ARCHITECTURE_FREEZE.md) |
| **J** | AI Copilot | LLM / agent adapters over frozen reports; domain remains LLM-agnostic — **J1.4 FROZEN** at `copilot` **0.5.0** · see [J1.4](J1_4_AI_COPILOT_VALIDATION_FREEZE.md) · [J0.0A](J0_0A_AI_COPILOT_ARCHITECTURE_FREEZE.md) |
| **K** | Platform Integration | **K1.4 FROZEN** · RC **v1.0.0-rc1** · **L1.0** Web Foundation `apps/web` · see [K1.4](K1_4_PLATFORM_FREEZE.md) · [L1.0](L1_0_WEB_APPLICATION_FOUNDATION.md) |

**Additive expansion only.** New packages or app layers may be introduced.
Frozen contracts change only via explicit freeze amendment.

---

## 8. Version baseline

Platform baseline **v1.0** freezes the following qualitative stack:

| Subsystem | Status | Package baseline (as of P1.0) |
|---|---|---|
| Analysis Framework | **FROZEN / BASELINE v1.0** | Engine / contracts stack (platform qualitative consumer of analysis) |
| Decision Intelligence | **FROZEN / BASELINE v1.0** | `decision_intelligence` |
| Industry Evidence Framework | **FROZEN / BASELINE v1.0** | `industry` |
| Comparison | **COMPLETE / BASELINE v1.0** | `comparison` |
| Portfolio Intelligence | **FROZEN / BASELINE v1.0** | `portfolio` **0.5.0** |
| Qualitative Risk Intelligence | **FROZEN / BASELINE v1.0** | `risk` **0.5.0** |
| Research Intelligence | **FROZEN / BASELINE v1.0** | `research` **0.4.0** |

**Suite at baseline freeze:** **1242 / 1242** passing.

### Authoritative subsystem freeze documents

| Subsystem | Freeze / validation docs |
|---|---|
| Portfolio | C4.0A · C4.5 · C4.6 |
| Risk | E0.0A · E1.5 |
| Research | F0.0A · F0.0B · F1.4 |
| Industry | C3.0A (and related) |
| Platform | **This document (P1.0)** |

---

## 9. PASS criteria

| Criterion | Status |
|---|---|
| Architecture frozen | ✓ |
| Ownership frozen | ✓ |
| Dependencies frozen | ✓ |
| Future additive expansion only | ✓ |
| No redesign required for E2 / G / H / I / J | ✓ |

---

## 10. Freeze confirmation

**CONFIRMED.**

DSP Architecture Baseline **v1.0** is complete. It is the authoritative
architectural reference for all future development on the DSP AI Indicator
platform.

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | **Platform architecture baseline v1.0** |
| [F1_4_RESEARCH_VALIDATION_AND_FREEZE.md](F1_4_RESEARCH_VALIDATION_AND_FREEZE.md) | Research F1 freeze |
| [E1_5_RISK_VALIDATION_AND_FREEZE.md](E1_5_RISK_VALIDATION_AND_FREEZE.md) | Risk E1 freeze |
| [C4_5_PORTFOLIO_VALIDATION_AND_FREEZE.md](C4_5_PORTFOLIO_VALIDATION_AND_FREEZE.md) | Portfolio static freeze |
| [F0_0A_RESEARCH_INTELLIGENCE_ARCHITECTURE_FREEZE.md](F0_0A_RESEARCH_INTELLIGENCE_ARCHITECTURE_FREEZE.md) | Research architecture |
| [E0_0A_RISK_INTELLIGENCE_ARCHITECTURE_FREEZE.md](E0_0A_RISK_INTELLIGENCE_ARCHITECTURE_FREEZE.md) | Risk architecture |

---

## Final question

Is DSP Architecture Baseline v1.0 complete and ready to serve as the
authoritative architectural reference for all future development?

**YES**
