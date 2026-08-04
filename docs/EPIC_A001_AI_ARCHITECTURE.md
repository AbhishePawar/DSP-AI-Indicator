# EPIC-A001 — AI Research Copilot Architecture

Status: **COMPLETE** · Priority: P0

## Flow

```
POST /api/v1/research/copilot/ask
   question + optional R001/R002/R004/R005 payloads
        ↓
QuestionProcessor  → intent/topics (deterministic)
ContextBuilder     → assemble platform artifacts (read-only)
PromptBuilder      → audited prompt descriptor (no provider call)
GroundedAnswer     → extractive section facts + citations
ResponseValidator  → require citations / Data unavailable.
```

## Rules

- Platform outputs only
- Never call market/fundamental providers
- Never calculate / value / score
- Never recommend beyond existing report text
- Missing → `"Data unavailable."`

## Package

`dsp_platform/research_copilot/` + `research_copilot_facade.py`
