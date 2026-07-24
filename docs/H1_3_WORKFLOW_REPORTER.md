# Phase H1.3 — Workflow Reporter

**Status:** Implemented · Presentation only · No orchestration  

**Package:** `packages/workflow/` **0.4.0**  
**Freeze:** [H0.0A](H0_0A_WORKFLOW_INTELLIGENCE_ARCHITECTURE_FREEZE.md)  
**Engine:** [H1.2](H1_2_WORKFLOW_ENGINE.md)

## Reporter architecture

```text
WorkflowReport  ──┐
EngineResult    ──┼──► ReportingContext
                  │
                  ▼
          WorkflowReporter
                  │
                  ├── ReportMetadata + summary sections
                  ├── ExecutionSection[] (per-step, ordered)
                  ├── ExecutionAudit (pass-through)
                  ├── StepExecutionResult[] (from engine, if present)
                  ├── retry history / failure summary
                  ├── referenced subsystem outcome ids
                  ├── WorkflowReport (limitations append only)
                  └── ReportingResult
```

APIs: `WorkflowReporter`, `ReportingContext`, `ReportingResult`,
`ReportingStatus`, `ReportMetadata`, `ExecutionSection`.

## Presentation policy

| Present | Behavior |
|---|---|
| Workflow summary | Pass-through `WorkflowSummary` |
| Execution state | Report / metadata `WorkflowState` |
| Step execution results | Pass-through engine `StepExecutionResult[]` |
| Execution audit | Pass-through `ExecutionAudit` |
| Retry history | Filter attempts with `attempt > 1` or multi-attempt steps |
| Failure summary | Collect `FailureDescriptor` without reinterpretation |
| Workflow metadata | Pass-through `WorkflowMetadata` |
| Referenced outcomes | Ordered unique ref ids + execution citations |

## Audit presentation

Audit entries preserve engine ordering and provenance. Reporter never rewrites
execution records.

## Retry presentation

Retry history is a presentation filter over existing executions — never triggers
retries, sleeps, or scheduling.

## Failure presentation

Failures are listed as recorded `FailureDescriptor` values (class + message +
provenance). Reporter never invents or reclassifies failures.

## Validation rules

Missing workflow identity · engine/report identity mismatch · duplicate
execution sections · broken references · missing provenance · missing audit ·
duplicate metadata/summary sections · immutable outputs · duplicate ids in
`report_many`.

## Formatting policy

- Preserve workflow / execution ordering and provenance.  
- Preserve Decimal identity on retry descriptors (no recalculation).  
- Never calculate, retry, mutate source objects, or infer outcomes.  
- May append a presentation-only limitations note via `dataclasses.replace`.

## Future extension strategy

| Phase | Scope |
|---|---|
| **H1.4** | Validation & freeze | **DONE / FROZEN** ([H1.4](H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md)) |

Additive section keys / UI adapters outside this package. No redesign of
Models → Assembler → Engine → Reporter (H0.0A).

## Non-goals (this phase)

Orchestration, scheduling, retries, business analysis, recommendation
generation, workflow execution, persistence, charts, LLM reasoning.

## Related documents

| Doc | Role |
|---|---|
| [H1.2](H1_2_WORKFLOW_ENGINE.md) | Engine |
| [H1.1](H1_1_WORKFLOW_ASSEMBLER.md) | Assembler |
| [H1.0](H1_0_WORKFLOW_DOMAIN_MODELS.md) | Models |
| [H0.0A](H0_0A_WORKFLOW_INTELLIGENCE_ARCHITECTURE_FREEZE.md) | Freeze |
