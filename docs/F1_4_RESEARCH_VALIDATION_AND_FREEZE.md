# Phase F1.4 — Research Validation & Architecture Freeze

**Status:** **FROZEN** · Validation only · No package / business-logic changes in this phase

**Baseline:** `packages/research/` **0.4.0** (F1.0–F1.3)  
**Suite gate:** **1242 / 1242** passing (2026-07-21)

This phase validates and freezes the **Research Intelligence** subsystem as the
final qualitative orchestration layer of the DSP AI Indicator platform.

It does **not** implement LLM adapters, workflow automation, recommendation
engines, quantitative risk, optimization, or OMS.

Authoritative prior freezes:

- [F0.0A Architecture Freeze](F0_0A_RESEARCH_INTELLIGENCE_ARCHITECTURE_FREEZE.md)
- [F0.0B Architecture Hardening](F0_0B_RESEARCH_ARCHITECTURE_HARDENING.md)

On conflicts about ownership / dependencies / responsibilities, **F0.0A + this
document** win. On synthesis invariants / claim language / traceability,
**F0.0B + this document** win. This document freezes the **implemented** F1
surface.

---

## 1. Validation results

| Area | Result | Notes |
|---|---|---|
| Domain models | **PASS** | Immutable dataclasses; cite-don’t-embed; claim-language guards |
| Research Assembler | **PASS** | Construction / citations only (F1.1) |
| Research Synthesizer | **PASS** | Citation-structural synthesis only (F1.2) |
| Research Reporter | **PASS** | Presentation of existing artifacts only (F1.3) |
| Ownership | **PASS** | No leakage into DI / IEF / Comparison / Portfolio / Risk |
| Dependencies | **PASS** | Runtime deps = `{core}` only; local refs only |
| Responsibilities | **PASS** | Assembler ≠ Synthesizer ≠ Reporter |
| Traceability | **PASS** | Insight → Observation → Evidence required |
| Claim-language policy | **PASS** | F0.0B vocabulary + model guards |
| Immutability | **PASS** | Frozen dataclasses; report snapshots |
| Reference-only upstream | **PASS** | Decision / Evidence / Comparison / Portfolio / Monitoring / Risk refs |
| Extension readiness | **PASS** | E2 / Recommendation / Workflow / LLM / KG / Audit / Performance |

**Overall:** **PASS**

---

## 2. Ownership matrix

| Domain | Owns | Research relationship |
|---|---|---|
| **Decision Intelligence** | `DecisionPack` | Cited via `DecisionReference` |
| **Industry (IEF)** | Evidence bundles / methodology | Cited via `EvidenceReference` |
| **Comparison** | `ComparisonReport` | Cited via `ComparisonReference` |
| **Portfolio Intelligence** | `Portfolio`, Monitoring | Cited via `PortfolioReference` / `MonitoringReference` |
| **Risk Intelligence** | Risk artifacts + `IntegratedRiskContext` | Cited via `RiskReference` / `IntegratedRiskReference` |
| **Research Intelligence** | See frozen ownership list below | Aggregate owner of research artifacts only |
| **Recommendation / Optimizer / OMS** (future) | Actions / search / execution | External consumers — never owned here |
| **App / LLM / Workflow** (future) | Rendering / orchestration | Outside frozen domain |

### Research owns ONLY

| Artifact | Role |
|---|---|
| `ResearchIdentity` | Session / thesis identity |
| `ResearchProfile` | Aggregate root |
| `ResearchObservation` | Knowledge-state observation |
| `ResearchInsight` | Cite-backed synthesis statement |
| `ResearchConflict` | Descriptive conflict record |
| `ResearchGap` | Knowledge gap |
| `ResearchAgenda` | Ordered investigative plan |
| `ResearchPriority` | Categorical agenda priority (not a score) |
| `ResearchCoverage` | Knowledge-coverage posture |
| `ResearchSummary` | Descriptive counts / limitations |
| `ResearchReport` | Canonical immutable presentation snapshot |

### Research owns NONE of

`DecisionPack` · `EvidenceBundle` · `ComparisonReport` · `Portfolio` ·
Portfolio Monitoring · `RiskProfile` · `RiskReport` · `IntegratedRiskContext` ·
Recommendation artifacts · analysis engines · trading / optimization models.

Supporting local citation types (not upstream ownership):
`DecisionReference`, `EvidenceReference`, `ComparisonReference`,
`PortfolioReference`, `MonitoringReference`, `RiskReference`,
`IntegratedRiskReference`.

**No ownership leakage detected.**

---

## 3. Dependency graph

```text
                    ┌────────────┐
                    │ dsp_platform│  (composition root — re-exports)
                    └──────┬─────┘
                           │ imports
                           ▼
                    ┌────────────┐
                    │  research  │  ← FROZEN qualitative orchestration (0.4.0)
                    └──────┬─────┘
                           │
                           ▼
                        ┌──────┐
                        │ core │
                        └──────┘

Upstream DI / IEF / Comparison / Portfolio / Risk
are cited via local reference types only — not imported.

Reverse imports into research from:
  portfolio, risk, industry, decision_intelligence, comparison, contracts
→ NONE (no cycles)
```

**Confirmed:**

- One-way dependencies only  
- No reverse imports  
- No circular dependencies  
- No engines / providers / persistence / workflow / LLM SDKs in domain  

**Runtime dependencies:** `core` only.  
**Forbidden (confirmed absent from `packages/research/src`):**  
`dsp`, `fundamental`, `economic`, `valuation`, `data_engine`, `snapshot_bridge`,
`orchestration`, `recommendation`, `ai_committee`, `dsp_platform`,
`decision_intelligence`, `comparison`, `universe`, `contracts`, `portfolio`,
`risk`, `industry`.

---

## 4. Responsibility matrix

| Component | Owns | Must not |
|---|---|---|
| **Domain models** | Structure & invariants | Pipelines |
| **ResearchAssembler** | Immutable construction from citations | Synthesis, presentation invention |
| **ResearchSynthesizer** | Observations, insights, gaps, conflicts, priorities, agenda, summary | Re-running upstream engines; RiskLevel; Buy/Sell/Hold |
| **ResearchReporter** | Canonical `ResearchReport` presentation | Creating insights / conflicts / agenda |

```text
Assembler constructs
        ↓
Synthesizer synthesizes (citation-structural)
        ↓
Reporter presents
```

**No responsibility overlap detected.**

### Responsibility triangle (unchanged)

| Subsystem | Answers |
|---|---|
| **Monitoring** | What changed? |
| **Risk** | What is the qualitative implication? |
| **Research** | What should be investigated next? |

---

## 5. Architectural guardrails

Research **never**:

- Calculates valuation / intrinsic value / margin of safety / expected return  
- Calculates risk (qualitative RiskLevel assignment or quantitative metrics)  
- Changes Portfolio structure or weights  
- Creates recommendations  
- Generates BUY / SELL / HOLD  
- Optimizes allocations  
- Introduces quantitative scoring or ranking  
- Creates new domain facts (synthesizes over cited upstream facts only)  
- Reinterprets Evidence payloads  
- Recalculates Risk or recomputes Portfolio  

Claim-language guards reject forbidden attractiveness / certainty / trade terms.
Architecture tests enforce forbidden package imports.

---

## 6. Frozen surface

The following are **frozen** as of F1.4 (additive extension only thereafter):

| Surface | Frozen artifacts |
|---|---|
| Package | `packages/research/` **0.4.0** |
| Domain models | Identity, Profile, Observation, Insight, Conflict, Gap, Agenda, Priority, Coverage, Summary, Report |
| Local refs | Decision / Evidence / Comparison / Portfolio / Monitoring / Risk / IntegratedRisk |
| Assembly contract | `ResearchAssembler` + context / result / status |
| Synthesis contract | `ResearchSynthesizer` + context / result / status |
| Reporter contract | `ResearchReporter` + context / result / status |
| Enums | Priority / Gap / Conflict / Coverage / Assembly / Synthesis / Reporting statuses |
| Dependency graph | Allowed set = `{core}` (+ local refs; no upstream package imports in F1) |
| Ownership model | Consumer-only of DI / IEF / Comparison / Portfolio / Risk |

---

## 7. Future extension points (no redesign required)

| Future system | Integration pattern |
|---|---|
| **E2 Quantitative Risk** | Cite quant reports additively; never rewrite Research contracts |
| **Recommendation Engine** | Consumes `ResearchReport` / agenda externally — Research emits no actions |
| **Workflow layer** | Orchestrates investigation steps outside domain |
| **LLM adapters** | Render / assist from `ResearchReport`; domain remains LLM-agnostic |
| **Knowledge Graph** | Optional index over citations — not a Research aggregate root |
| **Audit layer** | Append-only consumption of immutable report snapshots |
| **Performance attribution** | External; may cite research agendas descriptively |

---

## 8. Risks

| Risk | Severity | Status |
|---|---|---|
| Research becomes a second Risk engine | High | Mitigated (posture vs knowledge split) |
| Evidence reinterpretation via insights | High | Mitigated (citation-structural synthesis; no providers) |
| Agenda becomes trade recommendations | High | Mitigated (non-goals + claim-language) |
| LLM coupling in domain | Medium | Mitigated (LLM-agnostic lock) |
| Priority mistaken for score | Medium | Mitigated (categorical enum only) |
| Synthesizer / Reporter dual report paths | Low | Accepted — Reporter is canonical presentation |

---

## 9. Technical debt

1. Synthesizer still emits a `ResearchReport`; Reporter remains the canonical
   presentation path (possible later de-dup without API break).  
2. F1 uses local reference types only (`core` dependency); optional future
   freeze amendment may add typed adapters to Portfolio/Risk citation objects
   without changing ownership.  
3. Conflict detection is structural (citation presence mismatches), not
   field-level Comparison re-execution — intentional.  
4. Persistence / registries / research memory deferred to infrastructure.  
5. Optional `ResearchIntegrator` (coordination bundle) never required for F1;
   additive if needed later.

---

## 10. Roadmap

| Phase | Scope | Status |
|---|---|---|
| **F0.0 / F0.0A / F0.0B** | Design + freeze + hardening | **DONE / FROZEN** |
| **F1.0–F1.3** | Models → Assembler → Synthesizer → Reporter | **DONE** |
| **F1.4** | Validation & architecture freeze (this document) | **DONE / FROZEN** |
| **Later** | LLM / workflow / KG / memory (outside domain) | Optional |

---

## 11. Freeze confirmation

**CONFIRMED.**

Research Intelligence (models, assembler, synthesizer, reporter, dependency
graph, ownership model, hardening invariants) is architecturally complete and
frozen at `packages/research/` **0.4.0**.

It is ready to serve as the **final qualitative orchestration layer** of the
DSP AI Indicator platform. Future Quantitative Risk, Recommendation, Workflow,
LLM, Knowledge Graph, Audit, and Performance systems may extend by **additive
consumers** without structural redesign of the frozen F1 contracts.

---

## 12. PASS / FAIL

**PASS**

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | **Authoritative Research (F1) validation & freeze** |
| [F0_0A_RESEARCH_INTELLIGENCE_ARCHITECTURE_FREEZE.md](F0_0A_RESEARCH_INTELLIGENCE_ARCHITECTURE_FREEZE.md) | Foundational architecture freeze |
| [F0_0B_RESEARCH_ARCHITECTURE_HARDENING.md](F0_0B_RESEARCH_ARCHITECTURE_HARDENING.md) | Invariants / claim language / traceability |
| [F1_0_RESEARCH_DOMAIN_MODELS.md](F1_0_RESEARCH_DOMAIN_MODELS.md) | Models |
| [F1_1_RESEARCH_ASSEMBLER.md](F1_1_RESEARCH_ASSEMBLER.md) | Assembler |
| [F1_2_RESEARCH_SYNTHESIZER.md](F1_2_RESEARCH_SYNTHESIZER.md) | Synthesizer |
| [F1_3_RESEARCH_REPORTER.md](F1_3_RESEARCH_REPORTER.md) | Reporter |
| [E1_5_RISK_VALIDATION_AND_FREEZE.md](E1_5_RISK_VALIDATION_AND_FREEZE.md) | Qualitative Risk freeze (upstream) |

---

## Final question

Is Research Intelligence fully validated, architecturally frozen, and ready to
serve as the final qualitative orchestration layer of the DSP AI Indicator
platform?

**YES**
