# Phase J1.1 — AI Copilot Conversation Engine & Context Builder

**Status:** Implemented · Intent routing + context assembly only · No LLM  

**Package:** `packages/copilot/` **0.2.0**  
**Freeze:** [J0.0A](J0_0A_AI_COPILOT_ARCHITECTURE_FREEZE.md)  
**Models:** [J1.0](J1_0_AI_COPILOT_DOMAIN_MODELS.md)

## Conversation lifecycle

```text
ConversationEngineContext
        │
        ▼
ConversationEngine
  · detect / accept UserIntent (frozen taxonomy)
  · validate ConversationState transitions
  · append ConversationTurn
        │
        ▼
ContextBuilder → ContextBundle (KG required)
        │
        ▼
ConversationContext + ExplanationInput
        │
        ▼
ConversationResult
```

Session states follow frozen `ConversationState` with legal transitions
(`assert_legal_conversation_transition`).

## Intent routing

Deterministic keyword routing onto **frozen** `UserIntentType` only
(no financial calculations, no LLM):

| Mission alias (examples) | Frozen intent |
|---|---|
| EXPLAIN_REPORT / workflow query | `EXPLAIN_REPORT` |
| COMPARE_COMPANIES | `COMPARE_OUTCOMES` |
| VALUATION_QUERY / RISK_QUERY / PORTFOLIO_QUERY / RECOMMENDATION_QUERY | `SUMMARIZE_POSTURE` |
| graph / lineage questions | `NAVIGATE_GRAPH` |
| evidence questions | `TRACE_EVIDENCE` |
| CLARIFICATION_REQUIRED | `CLARIFY` |
| trading / OMS asks | `OUT_OF_SCOPE` |

Empty / unmatched text → `UNKNOWN` / `CLARIFY`.

## Context assembly

`ContextBuilder` normalizes immutable report refs into `ContextBundle`:

- Requires `KnowledgeGraphReference`  
- Collects ordered unique digests  
- Never embeds upstream reports  
- Never mutates citations  

## Knowledge Graph integration

Read-only citation of `KnowledgeGraphReference` on every bundle and
`ExplanationInput`. No graph construction / traversal / engine invocation.

## Validation rules

Illegal conversation transitions · broken Knowledge Graph / report refs ·
duplicate report refs · identity mismatch (turn/session, context as_of) ·
duplicate turn ids · `run_many` session uniqueness · missing user input.

## APIs

| Type | Role |
|---|---|
| `ConversationEngine` | `validate_inputs`, `run`, `run_many`, `detect_intent` |
| `ContextBuilder` | `build` → `ContextBundle` |
| `ConversationEngineContext` | Engine input |
| `ConversationResult` | Engine output |
| `ConversationStatus` | COMPLETE / PARTIAL / CLARIFY / OUT_OF_SCOPE / FAILED |
| `ExplanationInput` | Prepared immutable input for J1.2 |

Domain `ConversationContext` (J1.0) is **produced** as an output artifact.

## Future extension strategy

| Phase | Scope |
|---|---|
| **J1.2** | Explanation Engine (+ LanguageModelPort) | **DONE** ([J1.2](J1_2_AI_COPILOT_EXPLANATION_ENGINE.md)) |
| **J1.3** | Reporter | **DONE** ([J1.3](J1_3_AI_COPILOT_REPORTER.md)) |
| **J1.4** | Validation & freeze | **DONE / FROZEN** ([J1.4](J1_4_AI_COPILOT_VALIDATION_FREEZE.md)) |

Additive intents / keyword catalogs only. No redesign of cite-only /
provider-neutral rules (J0.0A).

## Non-goals (this phase)

Explanation generation, LLM invocation, persistence, business calculations,
report mutation, Knowledge Graph construction.
