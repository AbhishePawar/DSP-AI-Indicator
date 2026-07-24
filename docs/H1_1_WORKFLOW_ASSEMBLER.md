# Phase H1.1 — Workflow Assembler

**Status:** Implemented · Construction / citation bind only · No execution  

**Package:** `packages/workflow/` **0.2.0**  
**Freeze:** [H0.0A](H0_0A_WORKFLOW_INTELLIGENCE_ARCHITECTURE_FREEZE.md)  
**Models:** [H1.0](H1_0_WORKFLOW_DOMAIN_MODELS.md)

## Assembler architecture

```text
AssemblyContext
  ├── WorkflowIdentity
  ├── WorkflowMetadata
  ├── WorkflowStep[]
  ├── WorkflowTransition[]
  └── upstream OutcomeReference[] (optional citations)
        │
        ▼
WorkflowAssembler.assemble
        │
        ├── initialize step states (PENDING | READY)
        ├── initialize workflow state (PENDING | READY)
        ├── build WorkflowExecution skeletons (attempt=1, no results)
        ├── ExecutionAudit
        ├── WorkflowSummary
        ├── WorkflowProfile
        ├── WorkflowReport (skeleton)
        └── AssemblyResult (status + warnings)
```

| Does | Does not |
|---|---|
| Validate identity / metadata / steps / refs | Execute workflow steps |
| Normalize / preserve citations | Invoke subsystem façades |
| Validate prerequisites (structural) | Evaluate business rules |
| Build deterministic execution skeletons | Perform retries / scheduling |
| Initialize PENDING / READY only | Advance to RUNNING / terminal |
| Populate retry descriptors from steps | Persist or schedule work |

## Construction policy

1. Require `WorkflowIdentity`, `WorkflowMetadata`, and ≥ 1 `WorkflowStep`.  
2. Reject illegal input step states other than `PENDING` / `READY`.  
3. Re-initialize each step: **READY** iff `prerequisite_step_ids` is empty;
   otherwise **PENDING**.  
4. Workflow state: **READY** iff every step is READY; otherwise **PENDING**.  
5. Emit one `WorkflowExecution` skeleton per step (`attempt=1`, matching step
   state, `started_at` = creation timestamp only, `ended_at=None`, no failure,
   no outcome refs).  
6. Build `ExecutionAudit`, `WorkflowSummary`, `WorkflowProfile`, and
   `WorkflowReport` skeleton with assembly limitation notes.

## Validation rules

| Rule | Behavior |
|---|---|
| Missing required references | Identity / metadata / steps required |
| Duplicate references | Duplicate `id` or `report_id` within a ref group |
| Duplicate workflow ids | `assemble_many` via `assert_unique_workflow_ids` |
| Duplicate execution / step ids | Rejected before profile construction |
| Broken report digests / ids | Rejected on provided refs |
| Broken transitions | Missing prereq / transition→step links |
| Illegal initial states | Input step state ∉ {PENDING, READY} |
| Invalid retry descriptors | Surfaced via `RetryPolicy` / assembler checks |

Upstream outcome refs are **optional** at assembly (citation placeholders). When
present they must be structurally valid.

## Reference normalization

Refs pass through frozen constructors (`id`, `report_id`, `version`, `digest`,
`status`, `generated_at`). Assembler never embeds upstream report payloads.

## Initial state policy

- Workflow: `PENDING` or `READY` only.  
- Steps: `PENDING` or `READY` only.  
- No `RUNNING`, `BLOCKED`, `COMPLETED`, `FAILED`, `CANCELLED`, `SUCCEEDED`, or
  `SKIPPED` at assembly time.

## Execution skeleton policy

Skeletons are immutable attempt placeholders for Engine (H1.2):

- Provenance: `workflow.assembler`  
- No failures, no retries performed, no façade outcomes  
- Timestamps: creation only (`started_at`); no end times  

## Future extension strategy

| Phase | Scope |
|---|---|
| **H1.2** | Workflow Engine — advance state / record real executions | **DONE** ([H1.2](H1_2_WORKFLOW_ENGINE.md)) |
| **H1.3** | Reporter — presentation / audit finalize | **DONE** ([H1.3](H1_3_WORKFLOW_REPORTER.md)) |
| **H1.4** | Validation & freeze | **DONE / FROZEN** ([H1.4](H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md)) |

Additive only: optional required-ref profiles, parallel-step graphs, gate
citations. No redesign of Models → Assembler → Engine → Reporter (H0.0A).

## Non-goals (this phase)

Orchestration, façade invocation, dependency execution, retries, scheduling,
persistence, state transitions beyond initialization, business analysis.

## Related documents

| Doc | Role |
|---|---|
| [H1.0](H1_0_WORKFLOW_DOMAIN_MODELS.md) | Domain models |
| [H0.0A](H0_0A_WORKFLOW_INTELLIGENCE_ARCHITECTURE_FREEZE.md) | Architecture freeze |
