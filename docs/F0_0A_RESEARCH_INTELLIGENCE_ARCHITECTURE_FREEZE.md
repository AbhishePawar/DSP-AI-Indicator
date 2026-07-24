# Phase F0.0A — Research Intelligence Architecture Freeze

**Status:** **FROZEN**  
**Date:** 2026-07-21  
**Preceded by:** [F0.0 Research Intelligence Design](F0_0_RESEARCH_INTELLIGENCE_DESIGN.md)  
**Prerequisite stack:** AIMF · DI · IEF · Comparison · Portfolio (C4 frozen) · Qualitative Risk (E1.5 frozen) · **1186 tests green**  
**This phase:** Architecture lock only — **no code, no packages, no package modifications**

---

## Freeze declaration

The following are **authoritative** until an explicit freeze amendment:

1. Research Intelligence is an **independent subsystem** (not a Risk or Portfolio extension).  
2. Research Intelligence is a **pure consumer** of DecisionPack, Evidence, Comparison, Portfolio, Monitoring, RiskReport, and IntegratedRiskContext.  
3. Research owns **only research artifacts** listed in §3.  
4. Research **synthesizes knowledge** — it never re-analyzes, never recalculates Risk, never recomputes Portfolio, never reinterprets Evidence.  
5. Cite-don’t-embed; cite-don’t-reinterpret Evidence; never re-run Comparison or Risk analysis.  
6. No BUY/SELL/OPTIMIZE/TRADE recommendations from Research.  
7. No composite attractiveness scores or rankings (`ResearchPriority` is categorical only).  
8. Research domain is **LLM-agnostic** — adapters / workflows / memory stay outside the frozen domain model.  
9. Target package location: **`packages/research/`** (create in F1.0).

Conflicts with this document lose unless a later dated freeze amendment supersedes them.  
On conflicts with F0.0 design prose, **this freeze wins**.

---

## 1. Frozen architecture

```text
DecisionPack ──────────────┐
EvidenceBundle ────────────┤
ComparisonReport ──────────┤
Portfolio ─────────────────┼── citations only (never owned by Research)
Portfolio Monitoring ──────┤
RiskReport ────────────────┤
IntegratedRiskContext ─────┘
                │
                ▼
        Research Intelligence   ← independent package: packages/research/
                │
                ├── ResearchIdentity
                ├── ResearchProfile
                ├── ResearchObservation / ResearchInsight
                ├── ResearchConflict / ResearchGap
                ├── ResearchAgenda / ResearchPriority
                ├── ResearchCoverage / ResearchSummary
                │
                ▼
           ResearchReport
```

| Research Intelligence **is** | Research Intelligence **is not** |
|---|---|
| Independent DSP subsystem | A Risk or Portfolio package module |
| Cross-subsystem knowledge orchestrator | A security-analysis engine |
| Producer of `ResearchReport` | Owner of DI / IEF / Comparison / Portfolio / Risk |
| Synthesis layer over frozen citations | Re-runner of upstream analyzers |
| Agenda / gap / conflict presenter | Trading, optimization, or forecasting engine |
| LLM-agnostic domain | An LLM product surface |

### Boundary one-liners (frozen)

| Subsystem | Answers |
|---|---|
| **Decision Intelligence** | “Should I own it?” (single name) |
| **Portfolio Monitoring** | “What changed?” |
| **Risk Intelligence** | “What is the qualitative implication?” (posture) |
| **Research Intelligence** | “What should be investigated next?” (knowledge) |

---

## 2. Dependency graph

```text
contracts / core
        ▲
        │
portfolio (Portfolio, Monitoring, citation types)
risk (RiskReport, IntegratedRiskContext, citation types)
industry (EvidenceBundleReference — citation façade only)
        ▲
        │  one-way consume
        │
packages/research/   ← FROZEN target location (create in F1.0)
        │
        ▼
dsp_platform (additive re-exports only)
```

### Allowed dependencies (F1.x)

`core`, `portfolio`, `risk`, and citation façades only (`industry` for
`EvidenceBundleReference` if needed). Prefer frozen local/ref types from
Portfolio and Risk where already available.

### Forbidden dependencies (F1.x)

`dsp`, `fundamental`, `economic`, `valuation`, `data_engine`,
`snapshot_bridge`, `orchestration`, `recommendation`, `ai_committee`,
Comparison **engine** (consume reports/refs only), IEF **providers/interpreters**,
Optimizer/OMS packages, LLM SDKs as domain dependencies, `dsp_platform`
(except as external re-exporter).

### Cycle ban

- Research may import Portfolio and Risk.  
- Portfolio and Risk must **never** import Research.  
- DI / IEF / Comparison must **never** import Research.

### Validation (architecture)

| Check | Result |
|---|---|
| Ownership leakage | **PASS** (rules locked; no package yet) |
| Cyclic imports | **PASS** (ban locked) |
| Responsibility overlap with Monitoring / Risk | **PASS** (triangle locked) |
| Future compatibility (LLM / workflow / KG / memory) | **PASS** (outside domain) |

---

## 3. Canonical contracts (closed set for F1.x)

| Model | Role |
|---|---|
| **ResearchIdentity** | Stable research-session / thesis identity |
| **ResearchProfile** | Aggregate root — cites upstream; owns only research artifacts |
| **ResearchObservation** | Knowledge-state observation (not risk posture) |
| **ResearchInsight** | Cite-backed cross-subsystem synthesis statement |
| **ResearchConflict** | Declared inconsistency between cited subsystem outputs |
| **ResearchGap** | Missing / incomplete knowledge (evidence, decision, comparison, risk, monitoring) |
| **ResearchAgenda** | Ordered investigation plan |
| **ResearchPriority** | Categorical priority (e.g. HIGH / MEDIUM / LOW / UNKNOWN) — **not a score** |
| **ResearchCoverage** | Knowledge-coverage posture across subsystems |
| **ResearchSummary** | Descriptive counts / limitation notes |
| **ResearchReport** | Canonical presentation artifact |

**Closed:** this set is frozen for F1.x unless a freeze amendment adds a root.  
Supporting enums/status/context/result/ref types may be added additively without
new aggregate roots.

### Construction split (frozen names for F1.x)

| Component | Owns | Must not |
|---|---|---|
| **ResearchAssembler** | Immutable `ResearchProfile` construction from citations | Synthesis of insights/gaps/conflicts/agenda |
| **ResearchSynthesizer** | Insights, gaps, conflicts, agenda, outstanding questions | Re-running upstream engines; RiskLevel assignment; quant |
| **ResearchReporter** | Canonical `ResearchReport` presentation | Creating new synthesis |

**Naming lock:** F1.2 component is **`ResearchSynthesizer`** (not Analyzer) to
prevent confusion with Risk/Portfolio analyzers and to encode “synthesize,
don’t re-analyze.”

Optional later: `ResearchIntegrator` for coordination bundles — additive only;
not required to start F1.0.

---

## 4. Ownership matrix

| Domain | Owns | Must not own |
|---|---|---|
| **Decision Intelligence** | DecisionPack | Research, Portfolio, Risk |
| **Industry (IEF)** | Evidence, Methodology, providers, interpreters | Research |
| **Comparison** | ComparisonReport | Research |
| **Portfolio** | Holdings, Constraints, Snapshots, Monitoring history, PortfolioReport | Research artifacts |
| **Risk Intelligence** | RiskProfile, RiskAssessment, RiskObservation, RiskDescriptor, RiskCoverage, RiskConstraint, RiskSummary, RiskReport, IntegratedRiskContext | Research artifacts |
| **Research Intelligence** | ResearchIdentity, ResearchProfile, ResearchObservation, ResearchInsight, ResearchConflict, ResearchGap, ResearchAgenda, ResearchPriority, ResearchCoverage, ResearchSummary, ResearchReport | DecisionPack, Evidence, Comparison, Portfolio, Monitoring, Risk artifacts, engines, trading, optimization, quant models |
| **E2 Quantitative Risk / Optimizer / OMS** | Metrics / search / execution (future) | Research ownership of upstream roots |
| **App / LLM adapters** (future) | Rendering / prompting / workflow | Domain model ownership |

**No ownership leakage** into upstream domains is permitted.

---

## 5. Responsibility matrix

| May | Must not |
|---|---|
| Construct `ResearchProfile` from citations | Own or embed DecisionPack / Evidence / Comparison / Portfolio / Risk |
| Synthesize cross-subsystem insights | Re-analyze securities, valuation, or technicals |
| Detect / record evidence and coverage gaps | Reinterpret Evidence or re-run IEF providers |
| Detect / record declared conflicts between cited outputs | Re-run Comparison engine |
| Generate research agenda and outstanding questions | Recalculate Risk or assign RiskLevel |
| Present `ResearchReport` | Recompute Portfolio weights / structure |
| Cite Monitoring changes as investigation triggers | Become a change log (that is Monitoring) |
| Use categorical `ResearchPriority` | Score, rank, or forecast attractiveness |

### Responsibility triangle (no overlap)

| Subsystem | Owns the answer to |
|---|---|
| **Monitoring** | What changed? |
| **Risk** | What is the qualitative implication? |
| **Research** | What should be investigated next? |

---

## 6. Non-goals (frozen)

Research **never** performs:

- Valuation  
- Security analysis  
- Risk calculations (qualitative or quantitative)  
- Portfolio calculations  
- Trading  
- Optimization  
- Forecasting  
- BUY / SELL recommendations  
- Quantitative models  
- LLM-specific reasoning as a domain dependency  

---

## 7. Future extension points (outside frozen domain)

| Extension | Pattern |
|---|---|
| **LLM adapters** | App / presentation layer consumes `ResearchReport`; never required by domain |
| **Workflow automation** | Orchestrates investigation steps externally |
| **Knowledge graph** | Optional index over citations — not a Research aggregate root |
| **Research memory** | Persistence / retrieval service — not domain ownership of upstream truth |
| **E2 Quantitative Risk** | Sibling train; Research may cite quant reports later via freeze amendment |
| **Optimizer / OMS** | External; Research emits no trade instructions |

These remain **outside** the frozen F1.x domain model.

---

## 8. Implementation roadmap (post-freeze)

| Phase | Scope | Status |
|---|---|---|
| **F0.0** | Design | **DONE** |
| **F0.0A** | Architecture freeze (this document) | **DONE / FROZEN** |
| **F0.0B** | Architecture hardening (invariants / claim language) | **DONE** — see [F0.0B](F0_0B_RESEARCH_ARCHITECTURE_HARDENING.md) |
| **F1.0** | Domain models in `packages/research/` | **DONE** — see [F1.0](F1_0_RESEARCH_DOMAIN_MODELS.md) |
| **F1.1** | ResearchAssembler | **DONE** — see [F1.1](F1_1_RESEARCH_ASSEMBLER.md) |
| **F1.2** | ResearchSynthesizer | **DONE** — see [F1.2](F1_2_RESEARCH_SYNTHESIZER.md) |
| **F1.3** | ResearchReporter | **DONE** — see [F1.3](F1_3_RESEARCH_REPORTER.md) |
| **F1.4 / F1.x** | Validation & freeze | **DONE / FROZEN** — see [F1.4](F1_4_RESEARCH_VALIDATION_AND_FREEZE.md) |

**F1.0 acceptance gate:**

1. This freeze remains in force.  
2. New work lives in `packages/research/` with dependencies ⊆ allowed set (§2).  
3. Existing **1186+** tests stay green; Research changes are additive.  
4. No ranking/scoring types; no engine/provider/interpreter/LLM SDK imports in domain; no BUY/SELL/quant in F1.x.

---

## 9. Risks

| Risk | Severity | Status |
|---|---|---|
| Research becomes a second Risk engine | High | Mitigated (posture vs knowledge split) |
| Evidence reinterpretation via insights | High | Mitigated (cite-only; no providers) |
| Agenda becomes trade recommendations | High | Mitigated (non-goals + claim-language expectation) |
| LLM coupling in domain | Medium | Mitigated (LLM-agnostic lock) |
| Priority mistaken for score | Medium | Mitigated (categorical enum only) |
| Conflict detection re-runs Comparison | High | Mitigated (declared/structural citation conflicts only) |

---

## 10. Technical debt / deferred decisions

1. Exact Monitoring citation depth (ref only vs change-event refs) — decide in F1.0 models.  
2. Conflict detection: structural citation mismatches only in F1.2; no field-level re-comparison.  
3. Whether F1.4 needs `ResearchIntegrator` — optional additive.  
4. Persistence / registries deferred.  
5. Claim-language guard word list — align with Portfolio / Risk in F1.0.

---

## 11. Freeze confirmation

**CONFIRMED.**

Research Intelligence architecture (independence, ownership, dependency graph,
canonical contracts, Assembler / Synthesizer / Reporter split, Monitoring /
Risk / Research triangle, non-goals, extension points) is frozen and stable
enough to begin **F1.0** implementation without structural redesign of
upstream freezes.

---

## 12. PASS / FAIL

**PASS** — Research Intelligence architecture is frozen.

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | **Authoritative Research Intelligence architecture freeze** |
| [F1_4_RESEARCH_VALIDATION_AND_FREEZE.md](F1_4_RESEARCH_VALIDATION_AND_FREEZE.md) | **Implemented F1 validation & freeze** |
| [F0_0B_RESEARCH_ARCHITECTURE_HARDENING.md](F0_0B_RESEARCH_ARCHITECTURE_HARDENING.md) | Additive hardening (invariants / claim language / traceability) |
| [F0_0_RESEARCH_INTELLIGENCE_DESIGN.md](F0_0_RESEARCH_INTELLIGENCE_DESIGN.md) | Design review (historical; superseded on conflicts) |
| [E1_5_RISK_VALIDATION_AND_FREEZE.md](E1_5_RISK_VALIDATION_AND_FREEZE.md) | Qualitative Risk freeze (upstream) |
| [C4_5_PORTFOLIO_VALIDATION_AND_FREEZE.md](C4_5_PORTFOLIO_VALIDATION_AND_FREEZE.md) | Portfolio freeze |
| [E0_0A_RISK_INTELLIGENCE_ARCHITECTURE_FREEZE.md](E0_0A_RISK_INTELLIGENCE_ARCHITECTURE_FREEZE.md) | Risk architecture freeze |

---

## Final question

Is the Research Intelligence architecture frozen and stable enough to begin
implementation?

**YES**
