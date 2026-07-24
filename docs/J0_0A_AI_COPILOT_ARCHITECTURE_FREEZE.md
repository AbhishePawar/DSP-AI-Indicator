# Phase J0.0A — AI Copilot Architecture Freeze

**Status:** **FROZEN**  
**Date:** 2026-07-21  
**Preceded by:** [J0.0 AI Copilot Design](J0_0_AI_COPILOT_DESIGN.md)  
**Prerequisite:** [DSP Architecture Baseline v1.0](DSP_ARCHITECTURE_BASELINE_v1_0.md) · Qualitative stack frozen · Quantitative Risk E2.4 frozen · Recommendation G1.4 frozen · Workflow H1.4 frozen · Knowledge Graph I1.4 frozen · **1428 tests green**  
**This phase:** Architecture lock only — **no code, no packages, no package modifications**

---

## Freeze declaration

The following are **authoritative** until an explicit freeze amendment:

1. AI Copilot is an **independent bounded context**.  
2. Target package: **`packages/copilot/`** (create in J1.0).  
3. AI Copilot owns **only** the artifacts listed in §2.  
4. AI Copilot **orchestrates conversation and explanation only** — never
   performs financial analysis and never owns business facts.  
5. Interaction with frozen subsystems is **public façade / local reference only** —
   immutable reports and reference metadata only; no deep engine / assembler /
   reporter imports from upstream domains.  
6. Knowledge Graph is consumed **read-only** via public APIs /
   `KnowledgeGraphReport` citations — Copilot never constructs graphs.  
7. No reverse imports into Analysis / DI / IEF / Comparison / Portfolio / Risk /
   Research / Quant / Recommendation / Workflow / Knowledge Graph.  
8. Pipeline is frozen as **User Request → Conversation Engine → Context Builder
   → Knowledge Graph (read-only) → Explanation Engine → Reporter →
   CopilotResponse**.  
9. Domain remains **provider-neutral** via `LanguageModelPort` (§5).  
10. Persistence, vendor LLM SDKs, voice / multimodal transports, and chat
    stores live **outside** the domain (adapters only).

Conflicts with this document lose unless a later dated freeze amendment
supersedes them. On conflicts with J0.0 design prose, **this freeze wins**.

---

## 1. Architecture review

```text
AI Copilot (packages/copilot/)
        │
        │  intent / context / explanation / citations
        ▼
┌─────────────────────────────────────────────────────┐
│  Analysis · DI · IEF · Comparison · Portfolio       │
│  Qualitative Risk · Research · Quant · Recommend.   │
│  Workflow · Knowledge Graph                         │
│  (immutable reports + refs only — never owned)      │
└─────────────────────────────────────────────────────┘
        │
        ▼
    CopilotResponse
```

**Canonical pipeline (frozen):**

```text
User Request
        │
        ▼
Conversation Engine     (intent · routing · session / turns)
        │
        ▼
Context Builder         (ContextBundle from conversation + citations)
        │
        ▼
Knowledge Graph         (read-only navigation via KnowledgeGraphReport)
        │
        ▼
Explanation Engine      (evidence-backed Explanation; optional LLM port)
        │
        ▼
Copilot Reporter        (presentation only)
        │
        ▼
CopilotResponse
```

**Implementation mapping (J1.x — frozen shape):**

```text
Immutable Domain Models
        │
        ▼
Copilot Assembler / Context Builder
        │
        ▼
Conversation / Explanation Engine  (+ LanguageModelPort)
        │
        ▼
Copilot Reporter
        │
        ▼
CopilotResponse
```

| AI Copilot **is** | AI Copilot **is not** |
|---|---|
| Independent DSP bounded context | An extension of Knowledge Graph or Workflow |
| Conversation / explanation orchestrator | Business analysis engine |
| Producer of `CopilotResponse` | Owner of Decision / Risk / Recommendation / Workflow / KG facts |
| Cite-only consumer of frozen reports | Deep importer of upstream engines |
| Provider-neutral LLM consumer (port) | Vendor OpenAI / Anthropic / Gemini product |

**Sibling relationships (frozen):**

```text
Recommendation  →  "What should be done?"
Workflow        →  "In what order and under what conditions
                    should capabilities execute?"
Knowledge Graph →  "How are entities, reports, evidence,
                    and executions connected?"
AI Copilot      →  "How do we explain / navigate in natural language?"
Optimizer/OMS   →  "How do we search / place orders?" (future, external)
```

### Boundary one-liners (frozen)

| Subsystem | Answers |
|---|---|
| Frozen analysis domains | “What is true / what is the posture?” |
| **Recommendation** | “What should be done?” |
| **Workflow** | “How did execution happen?” |
| **Knowledge Graph** | “How are all platform entities, reports, and evidence connected?” |
| **AI Copilot** | “How do we explain those results to the user in natural language?” |
| Optimizer / OMS (future) | “How do we search / execute trades?” |

**Architecture validation:** **PASS**

---

## 2. Ownership matrix

| Domain | Owns | Copilot relationship |
|---|---|---|
| **AI Copilot** | Artifacts below | Conversation / explanation ownership only |
| **Frozen upstream domains + KG** | Their reports / engines | Cited via refs; never owned |
| **LLM / channel adapters** | Provider SDKs, streaming, voice | Outside domain via ports |
| **UI / API** | Rendering / transport | Consume `CopilotResponse` externally |

### AI Copilot owns ONLY

| Artifact | Role |
|---|---|
| `CopilotIdentity` | Copilot run / assistant / tenant identity |
| `ConversationSession` | Ordered conversation lifecycle container |
| `ConversationTurn` | Immutable user / assistant turn record |
| `ConversationContext` | Active session scope (as-of, focus, constraints) |
| `UserIntent` | Structured intent classification (routing — not a market conclusion) |
| `ContextBundle` | Assembled citation pack for one turn / explanation |
| `Explanation` | Evidence-backed structured explanation artifact |
| `CopilotSummary` | Counts / coverage / limitations |
| `CopilotProfile` | Aggregate root — cites upstream; owns conversation artifacts only |
| `CopilotResponse` | Canonical immutable presentation / chat response snapshot |
| `CopilotMetadata` | Model-agnostic run metadata (as-of, owner, tags, limitations) |

Supporting (not upstream ownership): local report / KG references, Assembler /
Engine / Reporter context·result·status types, intent taxonomy enums,
`LanguageModelPort` / request·result types.

### AI Copilot owns NONE of

Analysis · Decision · Industry Evidence · Comparison · Portfolio · Risk ·
Research · Quantitative Risk · Recommendation · Workflow · Knowledge Graph ·
Market Data · Trading · OMS · Persistence · Vendor LLM / channel SDKs.

**No ownership leakage.** Ownership validation: **PASS**

---

## 3. Dependency review

```text
copilot ──depends──► core
copilot ──depends──► LanguageModelPort (package-local port)
copilot ──cites──► immutable report outcomes (refs only)
copilot ──cites──► KnowledgeGraphReport (read-only public API / refs)
adapters (outside) ──implement──► LanguageModelPort
adapters (outside) ──may read──► upstream public façades
upstream domains / knowledge_graph ──✕──► copilot
```

### Frozen dependency rules

AI Copilot **SHALL**:

- Consume immutable reports only  
- Consume Knowledge Graph through public APIs / local refs only (read-only)  
- Use reference-only integration (ids, digests, versions, status, timestamps)  
- Depend only on `core` (+ stdlib) at package runtime  
- Depend on `LanguageModelPort` for generation / classification assistance  
- Never import vendor SDKs into domain core  
- Never create reverse imports  
- Never create dependency cycles  
- Never import upstream `engine` / `assembler` / `reporter` modules  

**Allowed runtime deps (J1.0+):** ⊆ `{core}` (+ stdlib).  

Dependency validation: **PASS**

---

## 4. Responsibilities

### AI Copilot SHALL

- Detect / classify `UserIntent`  
- Route conversation turns  
- Assemble `ContextBundle`  
- Navigate Knowledge Graph **read-only**  
- Generate `Explanation` artifacts  
- Aggregate evidence citations  
- Maintain conversation memory as domain session / turn artifacts  
- Handle citations and provenance  
- Preserve claim → citation traceability  

### AI Copilot SHALL NEVER

- Calculate financial metrics or intrinsic values  
- Generate recommendations  
- Execute workflows  
- Construct Knowledge Graph topology / lineage  
- Persist chat history as domain core behavior  
- Own market data, trading, or OMS  
- Recalculate analysis by reopening upstream engines  
- Invent facts when citations are missing  

---

## 5. LanguageModelPort contract (frozen)

The domain **SHALL remain provider-neutral**.

### Port surface (frozen shape)

```text
LanguageModelPort
    invoke(LanguageModelRequest) -> LanguageModelResult
```

| Type | Frozen fields (minimum) |
|---|---|
| `LanguageModelRequest` | `request_id`, `intent_class`, `prompt_parts` (structured, not free vendor schema), `context_digest_ids`, `constraints`, `provenance` |
| `LanguageModelResult` | `result_id`, `status`, `narrative_text` \| structured sections, `cited_digest_ids`, `model_label` (opaque string), `provenance`, `limitations` |
| Error classes | `PROVIDER_UNAVAILABLE` · `TIMEOUT` · `REFUSAL` · `INVALID_REQUEST` · `UNKNOWN` |

### Frozen rules

| Rule | Meaning |
|---|---|
| No vendor types in domain | OpenAI / Anthropic / Gemini / local SDK types forbidden in domain |
| Opaque model label | Adapter may set `model_label`; domain never branches on vendor enums |
| Citations required | Adapter results used in explanations must carry `cited_digest_ids` ⊆ ContextBundle |
| Optional LLM | Some intents may complete with template / structured explanation only |
| Deterministic stub | Tests use a stub adapter; no network required for domain tests |
| Refusal policy | Out-of-scope financial invention → `REFUSAL` + limitation notes |

### Supported adapters (future — additive)

OpenAI · Anthropic · Google Gemini · Local models · **future providers additive only**.

LanguageModelPort validation: **PASS**

---

## 6. Context policy (frozen)

Context **SHALL** be assembled only from:

1. Conversation state (`ConversationSession` / prior `ConversationTurn`s /
   `ConversationContext`)  
2. Immutable upstream reports (via local refs / digests)  
3. Knowledge Graph (`KnowledgeGraphReport` read-only)  
4. Current user request  

**Forbidden:** mutable business state, live engine re-execution, invented
holdings / scores / recommendations, writable KG mutation.

### Citation policy (required vs optional)

| Class | Reports / artifacts |
|---|---|
| **Strongly preferred for navigation** | `KnowledgeGraphReport` |
| **Commonly required for posture / action explanations** | Recommendation · Risk (qual and/or quant) · Workflow (when execution asked) |
| **Optional** | Analysis · Decision · Industry Evidence · Comparison · Portfolio · Research |

Missing citations → limitations / clarify intent — **never invent facts**.

Profiles may tighten required sets additively; loosening required → optional
needs freeze amendment only when changing platform-wide defaults.

Context policy validation: **PASS**

---

## 7. Explanation policy (frozen)

Every `Explanation` **SHALL**:

- Reference immutable evidence (digest-backed citations)  
- Maintain citation traceability (claim → `ContextBundle` → upstream digest)  
- Never invent facts  
- Never recalculate analysis  
- Clearly distinguish **evidence** (cited) from **generated narrative** (LLM or template)  

| Field expectation (design lock) | Rule |
|---|---|
| `evidence_refs` | Non-empty for factual claims; empty only for pure clarify / refusal |
| `narrative` | Marked as generated; not a substitute for missing evidence |
| `limitations` | Required when coverage incomplete or LLM refused |
| Provenance | Required on Explanation |

Explanation policy validation: **PASS**

---

## 8. Conversation policy (frozen)

### Lifecycle

| State (frozen set) | Meaning |
|---|---|
| `PENDING` | Session created; no user turn yet |
| `ACTIVE` | Accepting turns |
| `CLARIFYING` | Waiting on user clarification |
| `COMPLETED` | Graceful end |
| `FAILED` | Terminal failure (validation / provider / policy) |
| `CANCELLED` | User / system cancel |

### Session boundaries

- One `ConversationSession` owns an ordered sequence of `ConversationTurn`s.  
- Turns are immutable once recorded; corrections append new turns.  
- Session identity ≠ upstream report identity.

### Turn ownership

- User turns and assistant turns are first-class `ConversationTurn` records.  
- Assistant turns cite the `CopilotResponse` / `Explanation` produced for that turn.

### Intent routing (frozen classes)

| Intent class | Route |
|---|---|
| `EXPLAIN_REPORT` | Explain cited upstream report(s) |
| `NAVIGATE_GRAPH` | KG read-only navigation / lineage questions |
| `SUMMARIZE_POSTURE` | Summarize Decision / Risk / Recommendation citations |
| `TRACE_EVIDENCE` | Evidence aggregation / EvidenceLink walk (cite-only) |
| `COMPARE_OUTCOMES` | Present Comparison / multi-report contrasts |
| `CLARIFY` | Ask clarifying question; no factual invention |
| `UNKNOWN` / `OUT_OF_SCOPE` | Refusal / redirect; limitation notes |

Intent classes **must not** encode BUY / SELL / HOLD as Copilot conclusions.

### Context precedence (frozen)

1. Explicit user-supplied citation / focus in the current request  
2. Active `ConversationContext` focus  
3. Most recent assistant `ContextBundle` digests  
4. Profile defaults  

### Deterministic fallback behavior

| Condition | Fallback |
|---|---|
| Ambiguous intent | `CLARIFY` — do not guess financial conclusions |
| Missing required citations | Limitation notes + optional `CLARIFY` |
| LLM `REFUSAL` / unavailable | Structured template explanation from citations only, or fail closed with limitations |
| Out-of-scope trading / OMS ask | `OUT_OF_SCOPE` refusal — never invent orders |

Conversation policy validation: **PASS**

---

## 9. Architectural principles (frozen)

| Principle | Meaning |
|---|---|
| Single ownership | Upstream aggregates stay with frozen domains |
| Reference-only integration | Digests / ids / status / version only |
| Immutable inputs | Consume frozen reports; never mutate them |
| Conversation orchestration | Session / turn / intent / context — not analysis |
| Explainability-first | Citations + evidence/narrative separation required |
| Provider neutrality | `LanguageModelPort` only; no vendor SDKs in domain |
| No ownership leakage | Never absorb business facts, engines, or KG |

---

## 10. Extension model (frozen)

Future work remains **additive** — no redesign of ownership, cite-only rule,
KG read-only rule, or Conversation → Context → KG → Explanation → Reporter
pipeline:

| Extension | Pattern |
|---|---|
| Multi-agent orchestration | Additive coordinator + method ids outside core ownership |
| Tool calling | Adapter / port extensions; tools must not own upstream engines |
| Voice interfaces | Channel adapters outside domain |
| Multimodal conversations | Additive turn payloads / adapters |
| Streaming responses | Transport adapters; domain still emits immutable final `CopilotResponse` |
| Personalization | Additive profile fields; never mutate upstream reports |
| Human approval workflows | Cite Workflow / additive gate intents — do not own Workflow |

**Forbidden redesigns:** absorbing Knowledge Graph or Recommendation; making
Context Builder optional; embedding vendor SDKs in domain; recalculating
upstream analysis inside Copilot; writing to KG / Workflow engines.

---

## 11. Known technical debt (document only)

1. **Prompt management** — versioned prompt catalogs live in adapters /
   config, not as business ownership.  
2. **Conversation summarization** — long-session compaction is additive;
   durable store outside domain.  
3. **Long-context optimization** — windowing / retrieval budgets in adapters.  
4. **Retrieval tuning** — RAG / search indexes outside domain; KG remains
   cite-only navigation.  
5. **Safety guardrails** — policy filters as adapter / gateway layers.  
6. **LLM evaluation** — offline eval harnesses outside domain core.  
7. **Exact Assembler vs Context Builder naming** — J1.0 may use
   `CopilotAssembler` implementing Context Builder responsibilities.  
8. **Streaming partial events** — domain freezes final immutable response;
   partial events are transport-only.

---

## 12. Implementation roadmap (post-freeze)

| Phase | Scope | Status |
|---|---|---|
| **J0.0** | Design | **DONE** |
| **J0.0A** | Architecture freeze (this document) | **DONE / FROZEN** |
| **J1.0** | Domain models in `packages/copilot/` | **DONE** · see [J1.0](J1_0_AI_COPILOT_DOMAIN_MODELS.md) |
| **J1.1** | Assembler / Context Builder | **DONE** · see [J1.1](J1_1_AI_COPILOT_CONVERSATION_ENGINE.md) |
| **J1.2** | Conversation / Explanation Engine (+ LanguageModelPort) | **DONE** · see [J1.2](J1_2_AI_COPILOT_EXPLANATION_ENGINE.md) |
| **J1.3** | Reporter (`CopilotResponse`) | **DONE** · see [J1.3](J1_3_AI_COPILOT_REPORTER.md) |
| **J1.4** | Validation & freeze | **DONE / FROZEN** · see [J1.4](J1_4_AI_COPILOT_VALIDATION_FREEZE.md) |

**J1.0 acceptance gate:**

1. This freeze remains in force.  
2. Work lives in `packages/copilot/` with dependencies ⊆ `{core}`.  
3. Existing **1428+** tests stay green; changes are additive.  
4. No vendor LLM / persistence SDKs in domain; no financial analysis.  
5. Recommendation / Workflow / Quant / Research / Risk / Knowledge Graph
   freezes remain untouched.  
6. Knowledge Graph is read-only; Copilot never constructs topology.

---

## 13. Freeze confirmation

**CONFIRMED.**

AI Copilot architecture (independence, ownership, dependency direction,
Conversation → Context → KG(read-only) → Explanation → Reporter pipeline,
LanguageModelPort, context / explanation / conversation policies, extension
model) is fully frozen and ready for **J1.0** implementation.

---

## 14. PASS / FAIL

**PASS** — AI Copilot architecture is frozen.

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | **Authoritative AI Copilot architecture freeze** |
| [J0_0_AI_COPILOT_DESIGN.md](J0_0_AI_COPILOT_DESIGN.md) | Design (historical on conflicts) |
| [I1_4_KNOWLEDGE_GRAPH_VALIDATION_AND_FREEZE.md](I1_4_KNOWLEDGE_GRAPH_VALIDATION_AND_FREEZE.md) | Knowledge Graph freeze |
| [H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md](H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md) | Workflow freeze |
| [G1_4_RECOMMENDATION_VALIDATION_AND_FREEZE.md](G1_4_RECOMMENDATION_VALIDATION_AND_FREEZE.md) | Recommendation freeze |
| [DSP_ARCHITECTURE_BASELINE_v1_0.md](DSP_ARCHITECTURE_BASELINE_v1_0.md) | Platform baseline |

---

## Final question

Is the AI Copilot architecture fully validated, architecturally frozen,
and ready for implementation (J1.0)?

**YES**
