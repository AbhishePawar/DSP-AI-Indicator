# Phase H0.0 — Workflow Intelligence Architecture & Design

**Status:** Design review complete · **Superseded on conflicts by** [H0.0A Architecture Freeze](H0_0A_WORKFLOW_INTELLIGENCE_ARCHITECTURE_FREEZE.md)  
**Prerequisite:** [DSP Architecture Baseline v1.0](DSP_ARCHITECTURE_BASELINE_v1_0.md) · Qualitative stack frozen · Quantitative Risk **E2.4 FROZEN** · Recommendation **G1.4 FROZEN**  
**Suite gate:** **1328 / 1328** passing (2026-07-21)

## Verdict

**YES WITH CONDITIONS** (at design time) — conditions satisfied by H0.0A freeze.
See [H0.0A](H0_0A_WORKFLOW_INTELLIGENCE_ARCHITECTURE_FREEZE.md) for the
authoritative lock and **YES** to begin H1.0 implementation.

---

## 1. Recommended architecture

```text
Workflow Intelligence
(independent bounded context · process orchestration)
        │
        │  sequences / gates / retries / audit
        ▼
┌─────────────────────────────────────────────────────┐
│  Analysis Framework                                 │
│  Decision Intelligence                              │
│  Industry Evidence                                  │
│  Comparison                                         │
│  Portfolio                                          │
│  Qualitative Risk                                   │
│  Research                                           │
│  Quantitative Risk                                  │
│  Recommendation                                     │
└─────────────────────────────────────────────────────┘
        │
        │  step outcomes cited (report digests / status)
        ▼
    WorkflowReport
```

**Not a stack extension of Recommendation:**

```text
Recommendation answers:  "What should be done?"
Workflow answers:        "In what order and under what conditions
                          should platform capabilities execute?"

Optimizer / OMS (future) answer: "How do we search / execute trades?"
```

```text
Frozen domain packages
        ▲
        │ invoke via public façades / ports (one-way)
        │
packages/workflow/   ← proposed
        │
        ├── WorkflowIdentity / Profile
        ├── WorkflowStep / State / Transition
        ├── WorkflowExecution
        ├── WorkflowSummary
        │
        ▼
   WorkflowReport

dsp_platform → additive re-exports only
```

**Legacy note:** `packages/orchestration/` today hosts Sprint 7
`InvestmentAnalysisService` (Instrument → Data → Snapshots → Engines →
Committee). That package owns a **narrow analysis pipeline composer**. Epic H
Workflow Intelligence is a **broader process / approval / multi-subsystem
lifecycle** context. H0.0A must lock naming:

| Option | Notes |
|---|---|
| New `packages/workflow/` | **Preferred** — clear separation from Sprint 7 orchestration |
| Evolve `orchestration` into H | Risky — conflates committee pipeline with Workflow domain |

---

## 2. Design questions — decisions

### Q1 — Independent bounded context?

**Yes — independent bounded context.**

| Option | Verdict |
|---|---|
| Extend Recommendation (`packages/recommendation/`) | **Reject** — Recommendation is frozen decision synthesis (G1.4); workflow would violate freeze |
| Extend Research | **Reject** — Research answers investigation, not process lifecycle |
| Fold into `dsp_platform` only | **Reject** — needs stable domain ownership and contracts |
| Grow only Sprint 7 `orchestration` without redesign | **Reject as the H domain** — too narrow / committee-coupled |
| Independent Workflow Intelligence package | **Accept** |

**Rationale:**

1. Baseline v1.0 already reserves **Epic H** for investigation / approval
   orchestration **outside** analysis domain packages.  
2. Frozen subsystems must remain pure; Workflow coordinates **when / whether /
   in what order** they run.  
3. Recommendation must not absorb sequencing, retries, or human gates.  
4. Future Optimizer / OMS / Copilot need a stable `WorkflowReport` without
   owning business engines.

---

### Q2 — What should Workflow own?

| Artifact | Own? | Notes |
|---|---|---|
| `WorkflowIdentity` | **Yes** | Run / playbook / mandate identity |
| `WorkflowProfile` | **Yes** | Aggregate root — cites step outcomes; owns workflow artifacts only |
| `WorkflowStep` | **Yes** | Declared capability invocation (which subsystem / stage) |
| `WorkflowState` | **Yes** | Lifecycle state (e.g. pending / running / blocked / completed / failed) |
| `WorkflowTransition` | **Yes** | Allowed state change + guard condition descriptors |
| `WorkflowExecution` | **Yes** | Immutable record of a step attempt (status, timestamps, citations) |
| `WorkflowSummary` | **Yes** | Counts / failures / limitations |
| `WorkflowReport` | **Yes** | Canonical immutable presentation / audit snapshot |

**Supporting (citation-only):** local references to DecisionPack, EvidenceBundle,
ComparisonReport, Portfolio, RiskReport, ResearchReport, QuantitativeRiskReport,
RecommendationReport (digests / ids / run tokens — never embedded payloads).

**State vocabulary (design constraint for H0.0A):** Prefer explicit enums for
step status and workflow status. Avoid encoding business conclusions (BUY/SELL)
in WorkflowState.

---

### Q3 — What must Workflow never own?

| Artifact / concern | Why forbidden |
|---|---|
| Decision / Evidence / Comparison engines | Owned by DI / IEF / Comparison |
| Portfolio construction / monitoring engines | Owned by Portfolio |
| Qualitative / Quantitative Risk calculation | Owned by Risk / Quant |
| Research synthesis | Owned by Research |
| Recommendation generation / scoring | Owned by Recommendation (G1.4) |
| Market-data vendor adapters | data_engine / adapters |
| Trading strategies / order books | OMS / brokers |
| Optimizer search | Future Optimizer |
| Knowledge-graph storage | Epic I |
| LLM prompt loops as domain core | Copilot / adapters |

---

### Q4 — Which frozen outputs should Workflow consume?

| Upstream | Consume? | How |
|---|---|---|
| Analysis Framework | **Yes** | Invoke / cite run outcomes |
| Decision Intelligence | **Yes** | Cite `DecisionPack` / status |
| Industry Evidence | **Yes** | Cite EvidenceBundle refs |
| Comparison | **Yes** | Cite ComparisonReport |
| Portfolio | **Yes** | Cite Portfolio / Monitoring |
| Qualitative Risk | **Yes** | Cite RiskReport |
| Research | **Yes** | Cite ResearchReport |
| Quantitative Risk | **Yes** | Cite QuantitativeRiskReport |
| Recommendation | **Yes** | Cite RecommendationReport (esp. approval gates) |

**Dependency rules (proposed for H0.0A):**

1. **One-way only** — Workflow may invoke / cite upstream façades; upstream
   must **never** import Workflow domain.  
2. **Orchestrate, don’t analyze** — never recompute indicators, risk metrics,
   research insights, or recommendations.  
3. **Cite step outcomes** — store digests / ids / status, not full aggregates.  
4. **Runtime deps** — prefer `{core}` for domain models; composition adapters
   may call package façades from an application / adapter layer.  
5. **No vendor / broker / queue SDKs in domain core** — ports only.  
6. **Partial / failed steps** — recorded as executions + transitions; never
   invent missing upstream reports.

---

### Q5 — Responsibilities

| Responsibility | In scope? | Notes |
|---|---|---|
| Execution orchestration | **Yes** | Sequence frozen capability invocations |
| Step sequencing | **Yes** | Declared graphs / linear playbooks |
| Dependency management | **Yes** | Step prerequisites (e.g. Risk before Recommendation) |
| Retry policy | **Yes** | Declarative retry / backoff descriptors (adapters execute) |
| Failure reporting | **Yes** | Failed executions + limitations on WorkflowReport |
| Execution audit | **Yes** | Immutable execution history |
| Lifecycle management | **Yes** | State + transitions + human/system gates |
| Business analysis | **No** | Upstream domains |
| Recommendation synthesis | **No** | Recommendation |
| Optimization / trading | **No** | Optimizer / OMS |
| Durable scheduling / queues | **Adapter** | Outside domain core (H0.0A ports) |

**Proposed pipeline (design; freeze in H0.0A):**

```text
Models → (optional Assembler) → Workflow Engine → Reporter
                                         → WorkflowReport
```

- **Assembler:** bind playbook + citations / gate inputs.  
- **Engine:** advance states, record executions, apply transition guards
  (structural — not business scoring).  
- **Reporter:** presentation / audit snapshot only.

---

### Q6 — What remains outside Workflow?

| Outside | Owner |
|---|---|
| Business analysis / valuation / indicators | Analysis / DI / engines |
| Recommendation generation | Recommendation (G) |
| Portfolio optimization | Future Optimizer |
| Trading / OMS / brokerage | OMS |
| LLM reasoning / agents | Copilot / adapters |
| Knowledge graph indexing | Epic I |
| Concrete cron / queue / DB implementations | Infrastructure |
| Sprint 7 committee pipeline internals | `orchestration` (legacy composer) |

---

### Q7 — Relationship with Recommendation

| Subsystem | Answers |
|---|---|
| **Analysis / DI / IEF / Comparison** | “What is true?” |
| **Portfolio / Risk / Quant / Research** | Structure, risk posture, investigation |
| **Recommendation** | **“What should be done?”** |
| **Workflow** | **“In what order and under what conditions should platform capabilities execute?”** |
| **Optimizer / OMS** (future) | “How do we search / place orders?” |

**Boundary one-liner:** Workflow is the **process conductor**; Recommendation is
the **action advisor**. Workflow may **gate on** a `RecommendationReport` (e.g.
require human approval before a later step) but must never **author**
recommendation options or confidence.

---

## 3. Ownership matrix (summary)

| Domain | Owns | Workflow relationship |
|---|---|---|
| Frozen analysis / risk / research / recommendation packages | Their reports / engines | Invoked / cited only |
| **Workflow Intelligence** | Identity, Profile, Step, State, Transition, Execution, Summary, Report | Process ownership only |
| Infrastructure adapters | Schedulers, queues, persistence | Implement ports — outside domain |
| Optimizer / OMS / Copilot | Search / execution / UX | May trigger or consume WorkflowReport |

---

## 4. Dependency graph (proposed)

```text
contracts / core
        ▲
        │
frozen upstream packages (façade invoke + local refs)
        ▲
        │  one-way
        │
packages/workflow/   ← proposed H domain
        │
        └── models / engine / reporter
                │
                ▼
          WorkflowReport

Legacy packages/orchestration/  — parallel Sprint 7 composer (not H core)

dsp_platform → additive re-exports only
```

**Hard rules:**

- No reverse imports into frozen upstream domains.  
- No cycles.  
- No business logic leakage into WorkflowState.  
- No OMS / vendor SDKs in domain.

---

## 5. Non-goals (this phase)

- No implementation / no models / no package creation in H0.0  
- No orchestration runtime engine code  
- No scheduler / queue / persistence implementation  
- No recommendation or risk recalculation  

---

## 6. Future implementation roadmap

| Phase | Scope | Status |
|---|---|---|
| **H0.0** | Architecture & design (this document) | **DONE (design)** |
| **H0.0A** | Architecture freeze | **DONE / FROZEN** — see [H0.0A](H0_0A_WORKFLOW_INTELLIGENCE_ARCHITECTURE_FREEZE.md) |
| **H1.0** | Domain models | **DONE** · see [H1.0](H1_0_WORKFLOW_DOMAIN_MODELS.md) |
| **H1.1** | Assembler (playbook / citation bind) | **DONE** · see [H1.1](H1_1_WORKFLOW_ASSEMBLER.md) |
| **H1.2** | Workflow Engine (transitions / executions) | **DONE** · see [H1.2](H1_2_WORKFLOW_ENGINE.md) |
| **H1.3** | Reporter (`WorkflowReport`) | **DONE** · see [H1.3](H1_3_WORKFLOW_REPORTER.md) |
| **H1.4** | Validation & freeze | **DONE / FROZEN** · see [H1.4](H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md) |
| Later | Scheduler / queue / approval UI adapters | Infrastructure / app |

---

## 7. Risks & open items for H0.0A

| Item | Severity | Notes |
|---|---|---|
| Naming vs `packages/orchestration/` | High | Prefer new `workflow` package |
| Human approval gate model | High | Transition guards vs external workflow product |
| How deeply Workflow invokes vs only records citations | Medium | Prefer façade invoke via adapters |
| Retry / idempotency semantics | Medium | Declarative in domain; executed by adapters |
| Relationship to Recommendation approval | Medium | Gate on report id — never rewrite options |
| Premature BPM / Temporal coupling | High | Ports only — no vendor lock-in in domain |

---

## 8. PASS / FAIL

**PASS** — Workflow Intelligence architecture is sufficiently designed for
H0.0A freeze. No implementation performed in this phase.

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | Workflow Intelligence design (H0.0) |
| [DSP_ARCHITECTURE_BASELINE_v1_0.md](DSP_ARCHITECTURE_BASELINE_v1_0.md) | Platform baseline |
| [G1_4_RECOMMENDATION_VALIDATION_AND_FREEZE.md](G1_4_RECOMMENDATION_VALIDATION_AND_FREEZE.md) | Recommendation freeze (upstream consumer boundary) |
| [E2_4_QUANTITATIVE_RISK_VALIDATION_AND_FREEZE.md](E2_4_QUANTITATIVE_RISK_VALIDATION_AND_FREEZE.md) | Quant freeze |
| [F1_4_RESEARCH_VALIDATION_AND_FREEZE.md](F1_4_RESEARCH_VALIDATION_AND_FREEZE.md) | Research freeze |
| `packages/orchestration/` | Legacy Sprint 7 analysis pipeline composer (not H domain) |

---

## Final question

Is Workflow Intelligence sufficiently well-defined to become the next bounded
context of the DSP AI Indicator platform?

**YES WITH CONDITIONS**
