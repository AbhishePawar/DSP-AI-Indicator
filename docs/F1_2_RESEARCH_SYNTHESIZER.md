# Phase F1.2 — Research Synthesizer

**Status:** Implemented · Qualitative synthesis only

**Package:** `packages/research/` **0.3.0**

## Responsibilities

`ResearchSynthesizer` is the canonical **synthesis** layer for Research
Intelligence. It consumes an assembled `ResearchProfile` (and optional report /
citation overlays) and emits:

- structural `ResearchObservation`s (knowledge-state, cite-backed)
- `ResearchInsight`s (Evidence-provenanced)
- descriptive `ResearchConflict`s
- open `ResearchGap`s
- investigative `ResearchPriority` / `ResearchAgenda`
- updated `ResearchSummary` + `ResearchReport`

It never re-analyzes Evidence, recalculates Risk, recomputes Portfolio, or
recommends Buy/Sell/Hold.

## Synthesis pipeline

```text
ResearchProfile (+ optional citation overlays)
        ↓
validate ownership / evidence presence
        ↓
structural coverage from citation presence
        ↓
observations → gaps → conflicts → insights → priorities → agenda
        ↓
updated ResearchProfile + ResearchReport
        ↓
ResearchSynthesisResult (COMPLETE | PARTIAL | EMPTY)
```

## Traceability rules

```text
ResearchInsight
 ├── Observation IDs
 ├── EvidenceReference (required, ≥1)
 └── optional Decision / Comparison / Risk citations
```

Priorities cite gap / conflict / insight / observation ids. Conflicts record
left/right citation strings only — never resolved.

## Claim-language policy

Aligned with F0.0B. Preferred: observe, appear, indicate, evidence supports,
needs investigation, requires validation. Forbidden in artifact text: buy, sell,
hold, optimize, proves, guaranteed, certain, score, …

## Validation

Rejects missing EvidenceReference, foreign report ownership, foreign monitoring
vs portfolio. Model layer rejects duplicate synthesized collections and broken
insight provenance.

## Completeness status

| Status | Meaning |
|--------|---------|
| COMPLETE | Insights + agenda; no insufficient coverage dimensions |
| PARTIAL | Synthesis present; coverage gaps remain |
| EMPTY | No synthesis artifacts |
| FAILED | Reserved — validation errors raise |

## Extension guidance

- **F1.3** ResearchReporter — presentation only  
- LLM adapters / workflow remain outside domain  

## Non-goals

Reporter, recommendation engine, workflow, LLM reasoning, portfolio
optimization, risk calculations, trading, forecasting, persistence.
