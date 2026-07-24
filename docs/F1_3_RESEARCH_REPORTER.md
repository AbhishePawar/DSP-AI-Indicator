# Phase F1.3 — Research Reporter

**Status:** Implemented · Presentation / assembly only

**Package:** `packages/research/` **0.4.0**

## Responsibilities

`ResearchReporter` is the canonical **presentation** layer for Research
Intelligence. It assembles existing synthesized artifacts into an immutable
`ResearchReport`.

It never synthesizes insights, detects conflicts, creates agenda items, assigns
priorities, interprets Evidence, recalculates Risk, recomputes Portfolio, or
recommends actions.

## Reporting pipeline

```text
ResearchProfile (+ optional overlays / base_report)
        ↓
validate ownership / citations / duplicates / provenance
        ↓
resolve summary / coverage / insights / conflicts / gaps / agenda
        ↓
canonical immutable ResearchReport
        ↓
ResearchReportingResult (COMPLETE | PARTIAL | EMPTY)
```

## Report structure

`ResearchReport` includes:

- Identity (`research_id`) + `as_of`
- `ResearchSummary`
- `ResearchCoverage`
- Observations / Insights / Conflicts / Gaps
- Agenda (priorities)
- Citation metadata (Decision / Evidence / Comparison / Portfolio /
  Monitoring / Risk / IntegratedRisk refs)
- Traceability via insight → observation → evidence provenance
- Limitations

## Validation rules

Rejects:

- missing `ResearchSummary`
- missing `ResearchCoverage`
- missing Evidence citations
- broken / missing insight provenance
- duplicate report sections (insight / conflict / gap / coverage / priority)
- duplicate report identities in `report_many`
- foreign ownership (`base_report.research_id`)
- broken Decision / Evidence / Comparison digests

## Traceability

Reporter preserves synthesizer provenance. It does not create new observation
or evidence links. Insights without EvidenceReference or resolvable observation
ids are rejected.

## Completeness status

| Status | Meaning |
|--------|---------|
| COMPLETE | Insights + coverage + summary counts + agenda priorities |
| PARTIAL | Some sections present but incomplete |
| EMPTY | No insights, conflicts, or gaps |
| FAILED | Reserved — validation errors raise |

## Extension guidance

- **F1.4** Validation & architecture freeze  
- LLM / workflow presentation adapters remain outside domain  

## Non-goals

Synthesizer logic, workflow, recommendation, LLM, optimization, risk
calculations, forecasting, persistence, API providers.
