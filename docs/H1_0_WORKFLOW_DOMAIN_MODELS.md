# Phase H1.0 — Workflow Domain Models

**Status:** Implemented · Structure only · No assembler / engine / reporter  

**Package:** `packages/workflow/` **0.1.0**  
**Freeze:** [H0.0A](H0_0A_WORKFLOW_INTELLIGENCE_ARCHITECTURE_FREEZE.md)

## Domain ownership

Workflow owns **only**:

| Model | Role |
|---|---|
| `WorkflowIdentity` | Run / playbook / mandate identity |
| `WorkflowProfile` | Aggregate root |
| `WorkflowStep` | Declared capability invocation unit |
| `WorkflowTransition` | Allowed state change + guard descriptors |
| `WorkflowExecution` | Immutable attempt record |
| `WorkflowSummary` | Counts / limitations |
| `WorkflowReport` | Canonical immutable audit / presentation snapshot |
| `RetryPolicy` | Declarative retry descriptor |
| `FailureDescriptor` | Structured failure capture |
| `ExecutionAudit` | Ordered execution trail |
| `WorkflowMetadata` | Playbook / as-of / tags |

Workflow **never** owns: business analysis, Recommendation, Risk, Research,
Portfolio, Decision, market data, trading, OMS, scheduler implementations.

## Model hierarchy

```
WorkflowIdentity
WorkflowMetadata
RetryPolicy / FailureDescriptor
WorkflowStep ──────────────────────┐
WorkflowTransition ────────────────┤
WorkflowExecution ──► ExecutionAudit┤
                                   ▼
                         WorkflowProfile (aggregate)
                                   │
                                   ▼
                         WorkflowSummary
                                   │
                                   ▼
                         WorkflowReport
```

Upstream outcomes appear only as **reference citations** on Profile / Report.

## Reference model policy

Workflow SHALL reference upstream execution outcomes only. Never embed upstream
reports.

| Reference | Cites |
|---|---|
| `AnalysisReference` | Analysis Framework outcome |
| `DecisionReference` | DecisionPack |
| `IndustryEvidenceReference` | EvidenceBundle |
| `ComparisonReference` | ComparisonReport |
| `PortfolioReference` | Portfolio / monitoring outcome |
| `RiskReference` | Qualitative RiskReport |
| `ResearchReference` | ResearchReport |
| `QuantitativeRiskReference` | QuantitativeRiskReport |
| `RecommendationReference` | RecommendationReport |

Each reference contains **only**: `id`, `report_id`, `version`, `digest`,
`status`, `generated_at`.

## Validation rules

| Rule | Enforcement |
|---|---|
| Duplicate workflow ids | `assert_unique_workflow_ids` (batch / registry) |
| Duplicate execution ids | Profile / Report / Audit constructors |
| Duplicate step ids | Profile / Report constructors |
| Broken transitions | Missing prereq / step links; self-prereq |
| Illegal state transitions | `assert_legal_workflow_transition` / `assert_legal_step_transition` |
| Broken references | Execution `outcome_ref_ids` must cite known refs |
| Duplicate report references | Duplicate `id` or `report_id` within a ref group |
| Invalid retry configuration | Backoff / base / duplicate failure classes |
| Negative retry counts | `max_attempts` / `attempt` ≥ 1 |
| Missing provenance | Executions + FailureDescriptor |
| Decimal precision policy | `require_decimal` — no float |
| Immutable dataclasses | `frozen=True`, `slots=True` |

## Immutability policy

All domain models are frozen dataclasses. Mutating assignment raises
`AttributeError`. Assembler / Engine / Reporter (H1.1+) produce new instances;
they never mutate existing ones.

## State model

**WorkflowState:** `PENDING` · `READY` · `RUNNING` · `BLOCKED` · `COMPLETED` ·
`FAILED` · `CANCELLED`

**WorkflowStepState:** `PENDING` · `READY` · `RUNNING` · `SUCCEEDED` ·
`FAILED` · `SKIPPED` · `BLOCKED`

Business conclusions (`BUY` / `SELL` / `HOLD`) **must not** appear as workflow
or step states. Allowed transition maps live in `workflow.validation`.

## Retry model

`RetryPolicy` is declarative only:

- `max_attempts` ≥ 1  
- `BackoffPolicy`: `NONE` | `FIXED` | `EXPONENTIAL`  
- `backoff_base_ms` is `Decimal` when backoff ≠ `NONE`; must be `None` for `NONE`  
- `retryable_failure_classes` — unique `FailureClass` values  

Domain never sleeps, schedules, or performs retries. Adapters interpret policy.

## Failure model

`FailureClass`: `PREREQUISITE` · `UPSTREAM_FACADE` · `VALIDATION` · `TIMEOUT` ·
`GATE` · `CANCELLED` · `UNKNOWN`

`FailureDescriptor` requires non-empty `provenance`. Failed executions require
a `FailureDescriptor`.

## Public API

Stable façade: `workflow` package `__init__.py` exports models, enums, refs,
validation helpers, and `WorkflowError`. Version: **`0.1.0`**.

Platform re-exports via `dsp_platform` use `Workflow*` aliases for reference
types that collide with other domains (e.g. `WorkflowPortfolioReference`).

## Extension guidance

- **H1.1** Assembler — **DONE** ([H1.1](H1_1_WORKFLOW_ASSEMBLER.md))
- **H1.2** Engine — advance state / record executions  
- **H1.3** Reporter  
- Optimizer / OMS / Copilot remain external consumers  

## Non-goals (this phase)

Orchestration, façade invocation, workflow execution, scheduling,
persistence.

## Related documents

| Doc | Role |
|---|---|
| [H0.0A](H0_0A_WORKFLOW_INTELLIGENCE_ARCHITECTURE_FREEZE.md) | Architecture freeze |
| [H0.0](H0_0_WORKFLOW_INTELLIGENCE_DESIGN.md) | Design (historical on conflicts) |
| [DSP Architecture Baseline v1.0](DSP_ARCHITECTURE_BASELINE_v1_0.md) | Platform baseline |
