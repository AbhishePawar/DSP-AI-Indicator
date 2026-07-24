# Phase J1.3 — AI Copilot Reporter

**Status:** Implemented · Presentation only · No explanation / LLM  

**Package:** `packages/copilot/` **0.4.0**  
**Freeze:** [J0.0A](J0_0A_AI_COPILOT_ARCHITECTURE_FREEZE.md)  
**Explanation:** [J1.2](J1_2_AI_COPILOT_EXPLANATION_ENGINE.md)

## Responsibilities

Format immutable `ExplanationResult` into `CopilotResponse` for REST / UI /
mobile / CLI / SDK channels. Preserve evidence traceability and stable section
ordering. Never generate explanations or invoke LLMs.

## Ownership

Reporter owns presentation helpers only:

`CopilotReporter` · `ReportFormatter` · `ResponseFormatter` ·
`ResponseMetadataBuilder` · `CollectionStatistics` · `ValidationStatusView` ·
`ReportingContext` · `ReportingResult` · `ResponseMetadata`

Upstream reports / KG / engines remain cite-only inputs.

## Formatting pipeline

```text
ExplanationResult + ExplanationInput (+ CopilotMetadata)
        │
        ▼
ReportFormatter          (ordered sections)
        │
        ▼
ResponseMetadataBuilder  (presentation metadata)
        │
        ▼
ResponseFormatter        (immutable CopilotResponse)
        │
        ▼
ReportingResult
```

## Output contract

`CopilotResponse` includes identity, summary, explanation, intent, context
bundle, KG ref, citations (via explanation evidence_refs), metadata, status,
limitations.

`ReportingResult` additionally exposes executive summary, key reasons, risks,
supporting evidence, citations, confidence, provenance, statistics, and
validation view for channel adapters.

## Validation rules

Missing explanation · missing citations (except refuse/clarify) · broken
provenance · duplicate citations / evidence · invalid confidence / metadata ·
section-key duplicates · session/explanation identity alignment ·
`report_many` uniqueness · immutable outputs.

## Public API

Stable façade exports: `CopilotReporter`, `ReportFormatter`,
`ResponseFormatter`, `ResponseMetadataBuilder`, `ReportingContext`,
`ReportingResult`, `CollectionStatistics`, `ValidationStatusView`.

Version: **`0.4.0`**.

## Extension strategy / future API compatibility

| Phase | Scope |
|---|---|
| **J1.4** | Validation & architecture freeze | **DONE / FROZEN** ([J1.4](J1_4_AI_COPILOT_VALIDATION_FREEZE.md)) |

Additive section keys / channel serializers outside domain. No redesign of
Conversation → Explanation → Reporter pipeline (J0.0A).

## Non-goals (this phase)

Explanation generation, LLM invocation, Knowledge Graph traversal, report
mutation, workflow execution, persistence, calculations.
