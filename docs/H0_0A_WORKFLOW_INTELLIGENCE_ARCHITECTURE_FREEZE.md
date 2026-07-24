# Phase H0.0A — Workflow Intelligence Architecture Freeze

**Status:** **FROZEN**  
**Date:** 2026-07-21  
**Preceded by:** [H0.0 Workflow Intelligence Design](H0_0_WORKFLOW_INTELLIGENCE_DESIGN.md)  
**Prerequisite:** [DSP Architecture Baseline v1.0](DSP_ARCHITECTURE_BASELINE_v1_0.md) · Qualitative stack frozen · Quantitative Risk E2.4 frozen · Recommendation G1.4 frozen · **1328 tests green**  
**This phase:** Architecture lock only — **no code, no packages, no package modifications**

---

## Freeze declaration

The following are **authoritative** until an explicit freeze amendment:

1. Workflow Intelligence is an **independent bounded context**.  
2. Target package: **`packages/workflow/`** (create in H1.0) — **not** an
   evolution of Sprint 7 `packages/orchestration/`.  
3. Workflow owns **only** the artifacts listed in §3.  
4. Workflow **orchestrates execution only** — never performs business analysis
   and never owns business facts.  
5. Interaction with frozen subsystems is **public façade / local reference only** —
   no deep engine, assembler, or reporter imports from upstream domains.  
6. No reverse imports into Analysis / DI / IEF / Comparison / Portfolio / Risk /
   Research / Quant / Recommendation.  
7. Pipeline is frozen as **Models → Assembler → Workflow Engine → Reporter**.  
8. State machine, retry policy descriptors, and failure classification are
   frozen in §6–§8.  
9. Schedulers, queues, and persistence implementations live **outside** the
   domain (adapters only).

Conflicts with this document lose unless a later dated freeze amendment
supersedes them. On conflicts with H0.0 design prose, **this freeze wins**.

---

## 1. Frozen architecture

```text
Workflow Intelligence (packages/workflow/)
        │
        │  sequence / gate / retry descriptors / audit
        ▼
┌─────────────────────────────────────────────────────┐
│  Analysis · DI · IEF · Comparison · Portfolio       │
│  Qualitative Risk · Research · Quant · Recommend.   │
│  (public façades only — outcomes cited, never owned)│
└─────────────────────────────────────────────────────┘
        │
        ▼
    WorkflowReport
```

**Canonical pipeline (frozen):**

```text
Immutable Domain Models
        │
        ▼
Workflow Assembler   (normalize playbook + citations + gates)
        │
        ▼
Workflow Engine      (advance state / record executions)
        │
        ▼
Workflow Reporter    (presentation / audit only)
        │
        ▼
WorkflowReport
```

| Workflow **is** | Workflow **is not** |
|---|---|
| Independent DSP bounded context | An extension of Recommendation or Research |
| Process / lifecycle conductor | Business analysis engine |
| Producer of `WorkflowReport` | Owner of Decision / Risk / Recommendation facts |
| Façade-only subsystem coordinator | Deep importer of upstream engines |
| Audit-first execution recorder | Scheduler / queue / OMS product |

**Sibling relationships (frozen):**

```text
Recommendation  →  "What should be done?"
Workflow        →  "In what order and under what conditions
                    should platform capabilities execute?"
Optimizer/OMS   →  "How do we search / place orders?" (future, external)

Sprint 7 packages/orchestration/  →  narrow analysis pipeline composer
                                      (parallel legacy — not H core)
```

### Boundary one-liners (frozen)

| Subsystem | Answers |
|---|---|
| Frozen analysis domains | “What is true / what is the posture?” |
| **Recommendation** | “What should be done?” |
| **Workflow** | “In what order and under what conditions should capabilities execute?” |
| Optimizer / OMS (future) | “How do we search / execute trades?” |

---

## 2. Ownership matrix

| Domain | Owns | Must not own |
|---|---|---|
| **Workflow Intelligence** | Artifacts in §3 | Decision, Evidence, Comparison, Portfolio, Risk, Research, Quant, Recommendation, market data, trading, OMS, scheduler/queue implementations |
| **Frozen upstream domains** | Their reports / engines | Workflow state machines |
| **Infrastructure adapters** | Cron, queues, DB, brokers | Domain aggregates |
| **Legacy `orchestration`** | Sprint 7 analysis pipeline composition | Workflow Intelligence contracts |

### Workflow owns ONLY

| Artifact | Role |
|---|---|
| `WorkflowIdentity` | Run / playbook / mandate identity |
| `WorkflowProfile` | Aggregate root |
| `WorkflowStep` | Declared capability invocation unit |
| `WorkflowState` | Lifecycle state value object / enum binding |
| `WorkflowTransition` | Allowed state change + guard descriptors |
| `WorkflowExecution` | Immutable attempt record (status, times, citations) |
| `WorkflowSummary` | Counts / failures / limitations |
| `WorkflowReport` | Canonical immutable audit / presentation snapshot |

Supporting enums / status / context / result / package-local **ports**
(scheduler port, approval-gate port) may be added in H1.x without redesign.

### Workflow owns NONE of

`DecisionPack` · `EvidenceBundle` · `ComparisonReport` · `Portfolio` ·
qualitative / quantitative risk engines · `ResearchReport` ·
`RecommendationReport` ownership · market-data series · trading / OMS ·
concrete schedulers · concrete queues · LLM loops · knowledge-graph stores.

**No ownership leakage permitted.**

---

## 3. Dependency graph (frozen)

```text
contracts / core
        ▲
        │
frozen upstream packages
(public __init__ façades only — cited outcomes)
        ▲
        │  one-way invoke / cite
        │
packages/workflow/   ← FROZEN target (create in H1.0)
        │
        ├── models
        ├── assembler
        ├── engine
        └── reporter
                │
                ▼
          WorkflowReport

packages/orchestration/  — legacy parallel composer (not imported by workflow domain)

dsp_platform → additive re-exports only
```

### Dependency rules (frozen)

1. Domain runtime deps ⊆ `{core}` (plus package-local modules).  
2. **No direct imports** of upstream `engine` / `assembler` / `reporter`
   modules — **façade-only** (or adapter layer outside `workflow`).  
3. Consume **execution outcomes and references only** (digests / ids / status).  
4. **No reverse imports** from upstream domains into `workflow`.  
5. **No cycles.**  
6. **No vendor / broker / queue / scheduler SDKs** in domain core.  
7. Application adapters may call upstream façades; domain records citations.

---

## 4. Responsibilities (frozen)

### Workflow SHALL

- Sequence execution  
- Evaluate prerequisites  
- Coordinate execution order  
- Track execution state  
- Track transitions  
- Describe retry policy (descriptors — adapters execute)  
- Capture failures  
- Produce execution audit  
- Generate immutable `WorkflowReport`  

### Workflow NEVER

- Analyze investments  
- Generate recommendations  
- Calculate risk  
- Rewrite upstream reports  
- Optimize portfolios  
- Execute trades  
- Perform concrete scheduling / queueing  
- Embed LLM reasoning as domain core  

---

## 5. Architectural principles (frozen)

1. **Single ownership**  
2. **Immutable contracts**  
3. **Façade-only subsystem interaction**  
4. **Deterministic execution model** (same inputs → same transitions / audit)  
5. **Audit-first**  
6. **No hidden orchestration** (explicit steps, transitions, executions)  

---

## 6. Resolved design decisions (frozen)

### D1 — Assembler required?

**YES — Assembler is required.**

Execution requests / playbooks / gate citations require deterministic
normalization before the engine advances state.

**Frozen pipeline:** Models → **Assembler** → Workflow Engine → Reporter.

Assembler owns construction / citation bind / prerequisite declaration only —
never advances business conclusions.

### D2 — Workflow state machine

**Frozen workflow-level states (`WorkflowStatus`):**

| State | Meaning |
|---|---|
| `PENDING` | Accepted; not started |
| `READY` | Prerequisites satisfied; awaiting run |
| `RUNNING` | At least one step in flight |
| `BLOCKED` | Waiting on gate (e.g. human approval / missing prerequisite) |
| `COMPLETED` | Terminal success |
| `FAILED` | Terminal failure |
| `CANCELLED` | Terminal cancellation |

**Frozen step-level states (`StepStatus`):**

| State | Meaning |
|---|---|
| `PENDING` | Not started |
| `READY` | Prerequisites met |
| `RUNNING` | Invocation in progress |
| `SUCCEEDED` | Outcome cited |
| `FAILED` | Failed attempt recorded |
| `SKIPPED` | Explicitly skipped by transition guard |
| `BLOCKED` | Gate / dependency hold |

**Rules:**

- Transitions are explicit `WorkflowTransition` records.  
- Business conclusions (BUY/SELL/HOLD) **must not** appear as Workflow states.  
- Recommendation may be a **gate input** (cite `RecommendationReport`) —
  Workflow never authors recommendation options.

### D3 — Retry policy descriptor

**Frozen shape (domain descriptor — not a scheduler):**

| Field | Role |
|---|---|
| `max_attempts` | Inclusive attempt cap (≥ 1) |
| `backoff_policy` | `NONE` · `FIXED` · `EXPONENTIAL` |
| `backoff_base_ms` | Optional base delay descriptor |
| `retryable_failure_classes` | Subset of failure classes (§8) |
| `notes` | Human-readable limitations |

Adapters interpret descriptors. Domain never sleeps, cron-schedules, or enqueues.

### D4 — Failure classification

**Frozen failure classes (`WorkflowFailureClass`):**

| Class | Meaning |
|---|---|
| `PREREQUISITE` | Missing / unsatisfied dependency |
| `UPSTREAM_FAÇADE` | Invoked subsystem returned failure / invalid outcome |
| `VALIDATION` | Contract / reference validation failure |
| `TIMEOUT` | Declared time budget exceeded (adapter-reported) |
| `GATE` | Approval / external gate denied or expired |
| `CANCELLED` | Operator / system cancellation |
| `UNKNOWN` | Unclassified — must carry limitation notes |

Failures are recorded on `WorkflowExecution` and summarized on `WorkflowReport`.
Domain never invents missing upstream reports to “recover.”

---

## 7. Execution model (frozen)

1. Assembler binds identity + ordered steps + transitions + retry descriptors +
   upstream citation placeholders.  
2. Engine evaluates prerequisites / guards and records `WorkflowExecution`
   attempts.  
3. Successful steps cite outcome references (report digests / ids / status).  
4. Failed steps classify failure and optionally retry per descriptor.  
5. Terminal states emit immutable `WorkflowReport` via Reporter.  
6. Engine is **deterministic** given the same assembled profile, execution
   inputs, and adapter outcome records.

**Human approval** is a `BLOCKED`/`GATE` transition — recorded, not performed
as LLM reasoning inside the domain.

---

## 8. Extension model (frozen)

Future work remains **additive**:

| Extension | Pattern |
|---|---|
| Distributed / parallel execution | Additive step graph semantics + method ids |
| Checkpoint recovery | Additive execution checkpoints (immutable) |
| Human approval steps | Additive gate transitions (already reserved) |
| External schedulers | Adapter implementing package-local port |
| Message queues | Adapter only — never domain core |
| Deeper Recommendation gating policies | Cite report + additive guards |

**No redesign** of ownership, façade-only rule, or Models → Assembler → Engine →
Reporter pipeline.

---

## 9. Implementation roadmap (post-freeze)

| Phase | Scope | Status |
|---|---|---|
| **H0.0** | Design | **DONE** |
| **H0.0A** | Architecture freeze (this document) | **DONE / FROZEN** |
| **H1.0** | Domain models in `packages/workflow/` | **DONE** · see [H1.0](H1_0_WORKFLOW_DOMAIN_MODELS.md) |
| **H1.1** | Assembler | **DONE** · see [H1.1](H1_1_WORKFLOW_ASSEMBLER.md) |
| **H1.2** | Workflow Engine | **DONE** · see [H1.2](H1_2_WORKFLOW_ENGINE.md) |
| **H1.3** | Reporter | **DONE** · see [H1.3](H1_3_WORKFLOW_REPORTER.md) |
| **H1.4** | Validation & freeze | **DONE / FROZEN** · see [H1.4](H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md) |

**H1.0 acceptance gate:**

1. This freeze remains in force.  
2. Work lives in `packages/workflow/` with dependencies ⊆ allowed set.  
3. Existing **1328+** tests stay green; changes are additive.  
4. No vendor scheduler/queue/OMS SDKs in domain; no business analysis.  
5. Recommendation / Quant / Research / Risk freezes remain untouched.  
6. `packages/orchestration/` is not merged into Workflow without freeze amendment.

---

## 10. Known technical debt

1. Concrete façade-invoke adapter layout (app vs `dsp_platform`) deferred.  
2. Parallel / distributed step graphs intentionally underspecified beyond
   additive extension.  
3. Checkpoint / saga recovery semantics deferred.  
4. Exact human-approval UX outside domain.  
5. Relationship/documentation bridge from Sprint 7 `orchestration` to H
   remains a packaging clarity item — not a merge.  
6. Idempotency keys for step attempts — implement as additive field in H1.x.  

---

## 11. Freeze confirmation

**CONFIRMED.**

Workflow Intelligence architecture (independence, ownership, dependency
direction, Assembler-required pipeline, state machine, retry descriptors,
failure classification, façade-only interaction, extension model) is fully
frozen and ready for **H1.0** implementation.

---

## 12. PASS / FAIL

**PASS** — Workflow Intelligence architecture is frozen.

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | **Authoritative Workflow Intelligence architecture freeze** |
| [H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md](H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md) | Implemented H1 surface validation & freeze |
| [H0_0_WORKFLOW_INTELLIGENCE_DESIGN.md](H0_0_WORKFLOW_INTELLIGENCE_DESIGN.md) | Design (historical on conflicts) |
| [G1_4_RECOMMENDATION_VALIDATION_AND_FREEZE.md](G1_4_RECOMMENDATION_VALIDATION_AND_FREEZE.md) | Recommendation freeze |
| [DSP_ARCHITECTURE_BASELINE_v1_0.md](DSP_ARCHITECTURE_BASELINE_v1_0.md) | Platform baseline |

---

## Final question

Is Workflow Intelligence architecture fully frozen and ready for
implementation?

**YES**
