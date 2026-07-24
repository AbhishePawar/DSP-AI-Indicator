# Phase J1.0 — AI Copilot Domain Models

**Status:** Implemented · Structure only · No assembler / engine / reporter  

**Package:** `packages/copilot/` **0.1.0**  
**Freeze:** [J0.0A](J0_0A_AI_COPILOT_ARCHITECTURE_FREEZE.md)

## Ownership

AI Copilot owns **only**:

| Model | Role |
|---|---|
| `CopilotIdentity` | Copilot / assistant identity |
| `ConversationSession` | Ordered conversation lifecycle |
| `ConversationTurn` | Immutable user / assistant / system turn |
| `ConversationContext` | Active session scope |
| `UserIntent` | Structured routing intent |
| `ContextBundle` | Assembled citation pack |
| `Explanation` | Evidence-backed explanation artifact |
| `CopilotSummary` | Counts / limitations |
| `CopilotProfile` | Aggregate root |
| `CopilotResponse` | Canonical immutable presentation snapshot |
| `CopilotMetadata` | As-of / owner / tags |
| `LanguageModelRequest` | Provider-neutral LM request contract |
| `LanguageModelResult` | Provider-neutral LM result contract |

Upstream Analysis / Decision / Evidence / Comparison / Portfolio / Risk /
Research / Quant / Recommendation / Workflow / Knowledge Graph remain
**reference-only**.

## Model hierarchy

```
CopilotIdentity
CopilotMetadata
ConversationContext / UserIntent
ConversationTurn → ConversationSession
ContextBundle / Explanation
LanguageModelRequest / LanguageModelResult
        │
        ▼
CopilotProfile (aggregate)
        │
        ▼
CopilotSummary
        │
        ▼
CopilotResponse
```

## Reference policy

References contain only: `id`, `report_id`, `version`, `digest`, `status`,
`generated_at`. Never embed upstream reports.

**Required:** `KnowledgeGraphReference` on `CopilotProfile`, `ContextBundle`,
and `CopilotResponse`.

**Optional:** Analysis, Decision, Industry Evidence, Comparison, Portfolio,
Risk, Research, Quantitative Risk, Recommendation, Workflow.

## LanguageModelPort contract

Immutable contracts only (no provider implementation in this phase):

| Type | Role |
|---|---|
| `LanguageModelRequest` | `request_id`, `intent_class`, `prompt_parts`, `context_digest_ids`, `constraints`, `provenance` |
| `LanguageModelResult` | `result_id`, `status`, `narrative_text` / `structured_sections`, `cited_digest_ids`, opaque `model_label`, `provenance`, `limitations` |

Adapters (OpenAI / Anthropic / Gemini / local) remain outside the domain.

## Validation rules

Duplicate turn / session / intent / bundle / explanation ids · broken session /
turn links · illegal intent / conversation / explanation / response / LM
statuses · missing provenance · missing Knowledge Graph reference · factual
explanations require `evidence_refs` · duplicate report references · frozen
dataclasses.

## Immutability

All domain models are frozen dataclasses (`frozen=True`, `slots=True`).

## Enums

`ConversationState` · `ConversationRole` · `UserIntentType` ·
`ExplanationType` · `ResponseStatus` · `LanguageModelStatus`

## Public API

Stable façade: `copilot` package `__init__.py`. Version: **`0.1.0`**.

## Future extension strategy

| Phase | Scope |
|---|---|
| **J1.1** | Assembler / Context Builder | **DONE** ([J1.1](J1_1_AI_COPILOT_CONVERSATION_ENGINE.md)) |
| **J1.2** | Conversation / Explanation Engine (+ LanguageModelPort) | **DONE** ([J1.2](J1_2_AI_COPILOT_EXPLANATION_ENGINE.md)) |
| **J1.3** | Reporter (`CopilotResponse`) | **DONE** ([J1.3](J1_3_AI_COPILOT_REPORTER.md)) |
| **J1.4** | Validation & freeze | **DONE / FROZEN** ([J1.4](J1_4_AI_COPILOT_VALIDATION_FREEZE.md)) |

Vendor LLM / channel / persistence adapters remain external.

## Non-goals (this phase)

Conversation orchestration, explanation generation, LLM invocation,
persistence, business analysis, recommendation / workflow / graph engines.
