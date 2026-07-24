# Phase J1.2 — AI Copilot Explanation Engine

**Status:** Implemented · Evidence-backed explanations · Deterministic fallback  

**Package:** `packages/copilot/` **0.3.0**  
**Freeze:** [J0.0A](J0_0A_AI_COPILOT_ARCHITECTURE_FREEZE.md)  
**Conversation:** [J1.1](J1_1_AI_COPILOT_CONVERSATION_ENGINE.md)

## Architecture

```text
ExplanationInput (from ConversationEngine)
        │
        ▼
EvidenceValidator  (ContextBundle / citations / claim links)
        │
        ▼
ExplanationEngine
  · deterministic template draft
  · optional LanguageModelPort enrichment
  · fallback when LM unavailable / non-complete
        │
        ▼
ExplanationResult
  · Explanation (domain)
  · ExplanationDraft
  · structured sections
```

## APIs

| Type | Role |
|---|---|
| `ExplanationEngine` | `validate_inputs`, `explain`, `explain_many` |
| `ExplanationInput` | Immutable prepared input (J1.1) |
| `ExplanationDraft` | Intermediate structured sections |
| `EvidenceValidator` | Bundle + draft validation |
| `ExplanationResult` | Final structured output |
| `LanguageModelPort` | Optional provider-neutral Protocol |

## Output sections

Executive Summary · Key Reasons · Risks · Supporting Evidence · Confidence
(`ConfidenceLevel` citation coverage) · Citations · Provenance

## Evidence policy

- Every factual claim must cite digests present in `ContextBundle`  
- Evidence vs generated narrative distinguished (`is_generated_narrative`)  
- Knowledge Graph reference required and digest-linked  
- No invented facts; no recalculated analysis  

## Deterministic fallback

When `LanguageModelPort` is absent, raises, or returns non-complete status,
the engine emits a cite-only template `ExplanationDraft`
(`ExplanationType.EVIDENCE_SUMMARY`) and records a fallback warning.

## Validation rules

Missing evidence · unsupported claims · missing provenance · duplicate
citations · broken Knowledge Graph references · empty explanation ·
`explain_many` uniqueness.

## Non-goals (this phase)

Valuation · recommendation generation · market calculations · workflow
execution · persistence · report mutation · vendor LLM SDKs in domain.

## Future extension

| Phase | Scope |
|---|---|
| **J1.3** | Reporter (`CopilotResponse`) | **DONE** ([J1.3](J1_3_AI_COPILOT_REPORTER.md)) |
| **J1.4** | Validation & freeze | **DONE / FROZEN** ([J1.4](J1_4_AI_COPILOT_VALIDATION_FREEZE.md)) |
