# Phase F1.1 — Research Assembler

**Status:** Implemented · Construction only

**Package:** `packages/research/` **0.2.0**

## Responsibilities

`ResearchAssembler` is the canonical **constructor** for Research Intelligence.

It builds an immutable `ResearchProfile` and structural `ResearchReport` from
upstream **references only**.

It does **not** synthesize insights, detect conflicts/gaps, generate agenda
priorities, interpret evidence, or recommend actions.

## Construction pipeline

```text
ResearchIdentity + EvidenceReference (+ optional citations)
        ↓
validate ownership / duplicates / broken refs
        ↓
attach citations
        ↓
initialize empty observations / insights / conflicts / gaps
        ↓
empty ResearchAgenda + placeholder ResearchSummary
        ↓
initial structural ResearchCoverage (citation presence only)
        ↓
ResearchProfile + ResearchReport
        ↓
ResearchAssemblyResult (COMPLETE | PARTIAL | EMPTY)
```

Validation failures raise `ResearchError` (status enum includes `FAILED` for
contract completeness; successful assembly never returns `FAILED`).

## Validation rules

Rejects:

- missing `ResearchIdentity`
- missing `EvidenceReference` (at least one required)
- duplicate Decision / Evidence / Comparison / Risk / IntegratedRisk refs
- broken digests / empty ids
- foreign Monitoring vs Portfolio ownership
- Monitoring without Portfolio
- duplicate `research_id` in `assemble_many`

## Ownership

Assembler owns only construction of Research artifacts. Upstream DecisionPack,
Evidence, Comparison, Portfolio, Monitoring, and Risk remain cite-only.

## Traceability

Citations are attached to both profile and report. Empty synthesis collections
preserve a clean hand-off to F1.2 (`ResearchSynthesizer`), which must attach
Evidence provenance to every insight.

## Completeness status

| Status | Meaning |
|--------|---------|
| COMPLETE | Evidence + portfolio + monitoring + decision + comparison + risk citations |
| PARTIAL | Evidence + some optional citations |
| EMPTY | Evidence only (structural shell) |
| FAILED | Reserved — validation errors raise instead |

## Extension guidance

- **F1.2** ResearchSynthesizer — insights, gaps, conflicts, agenda  
- **F1.3** ResearchReporter — presentation  
- LLM / workflow / persistence remain outside the domain  

## Non-goals

Synthesizer, reporter, conflict/gap detection, agenda generation, priority
scoring, workflow, recommendation, LLM, trading, optimization, persistence.
