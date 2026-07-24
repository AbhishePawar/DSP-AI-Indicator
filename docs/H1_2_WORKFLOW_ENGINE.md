# Phase H1.2 — Workflow Engine

**Status:** Implemented · Façade-only orchestration · No business analysis  

**Package:** `packages/workflow/` **0.3.0**  
**Freeze:** [H0.0A](H0_0A_WORKFLOW_INTELLIGENCE_ARCHITECTURE_FREEZE.md)  
**Assembler:** [H1.1](H1_1_WORKFLOW_ASSEMBLER.md)

## Engine architecture

```text
AssemblyResult
  + SubsystemFacadePort (adapter)
  + EngineContext (cancel / skip / timestamp)
        │
        ▼
WorkflowEngine.run
        │
        ├── validate assembly / audit / identity
        ├── PENDING→READY (promote steps) → RUNNING
        ├── for each step (prereq order):
        │     READY→RUNNING → façade.invoke
        │     → SUCCEEDED | FAILED | BLOCKED | SKIPPED
        │     honor RetryPolicy (no sleep)
        ├── RUNNING→ COMPLETED | FAILED | BLOCKED
        ├── ExecutionAudit + ExecutionResult
        └── WorkflowProfile / WorkflowReport (updated)
```

APIs: `WorkflowEngine`, `EngineContext`, `EngineResult`, `EngineStatus`,
`ExecutionResult`, `StepExecutionResult`, `StepFacadeResult`,
`SubsystemFacadePort`.

## Execution lifecycle

1. Validate assembled profile / report / executions / audit.  
2. Optional cancel → terminal `CANCELLED` (no façade calls).  
3. Promote `PENDING` steps whose prerequisites are `SUCCEEDED`/`SKIPPED`.  
4. Advance workflow `PENDING|READY` → `READY` → `RUNNING`.  
5. For each step: evaluate prerequisites; skip if requested; otherwise invoke
   façade port and record immutable `WorkflowExecution` attempts.  
6. On retryable failure, increment attempt immediately (descriptor only — never
   sleep / schedule).  
7. Terminal workflow state → rebuild profile + report + summary/audit.

## State transition rules

**Workflow:** `READY→RUNNING→COMPLETED|FAILED` · `READY→BLOCKED|CANCELLED` ·
`PENDING→READY` · `PENDING→CANCELLED` · `RUNNING→BLOCKED`

**Step:** `READY→RUNNING→SUCCEEDED|FAILED|BLOCKED` · `READY→SKIPPED|BLOCKED` ·
`PENDING→READY` · `FAILED→RUNNING` (retry)

Illegal transitions raise `WorkflowError`.

## Retry behavior

- Honors `RetryPolicy.max_attempts` and `retryable_failure_classes`.  
- Records each attempt on the audit trail.  
- **Never** sleeps, delays, enqueues, or cron-schedules.  
- Retry overflow raises `WorkflowError`.

## Failure handling

Only documented `FailureClass` values: `PREREQUISITE`, `UPSTREAM_FACADE`,
`VALIDATION`, `TIMEOUT`, `GATE`, `CANCELLED`, `UNKNOWN`.  
Failures attach `FailureDescriptor` with provenance; never invent upstream
reports.

## Audit policy

- Assembler skeletons retained; engine appends per-attempt executions.  
- Provenance includes `workflow.engine` + façade provenance.  
- Duplicate execution ids rejected.  
- Missing audit / executions rejected at validate.

## Validation rules

Illegal transitions · missing execution / workflow / audit · broken façade
outcome refs · duplicate execution results · retry overflow · broken
provenance · engine/report identity mismatch · duplicate ids in `run_many`.

## Future extension strategy

| Phase | Scope |
|---|---|
| **H1.3** | Reporter — presentation / audit finalize | **DONE** ([H1.3](H1_3_WORKFLOW_REPORTER.md)) |
| **H1.4** | Validation & freeze | **DONE / FROZEN** ([H1.4](H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md)) |

Additive: richer gate ports, parallel-step graphs, checkpoint fields. No
redesign of Models → Assembler → Engine → Reporter (H0.0A).

## Non-goals (this phase)

Business analysis, recommendation generation, market calculations,
persistence, queues, schedulers, distributed execution, LLM reasoning,
upstream report mutation, deep imports of upstream engines.

## Related documents

| Doc | Role |
|---|---|
| [H1.1](H1_1_WORKFLOW_ASSEMBLER.md) | Assembler |
| [H1.0](H1_0_WORKFLOW_DOMAIN_MODELS.md) | Models |
| [H0.0A](H0_0A_WORKFLOW_INTELLIGENCE_ARCHITECTURE_FREEZE.md) | Freeze |
