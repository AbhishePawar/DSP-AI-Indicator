# Phase J0.0 — AI Copilot Architecture & Design

**Status:** Design review complete · **Superseded on conflicts by** [J0.0A Architecture Freeze](J0_0A_AI_COPILOT_ARCHITECTURE_FREEZE.md)  
**Prerequisite:** [DSP Architecture Baseline v1.0](DSP_ARCHITECTURE_BASELINE_v1_0.md) · Qualitative stack frozen · Quantitative Risk **E2.4 FROZEN** · Recommendation **G1.4 FROZEN** · Workflow **H1.4 FROZEN** · Knowledge Graph **I1.4 FROZEN**  
**Suite gate:** **1428 / 1428** passing (2026-07-21)

## Verdict

**YES WITH CONDITIONS** (at design time) — conditions satisfied by J0.0A freeze.
See [J0.0A](J0_0A_AI_COPILOT_ARCHITECTURE_FREEZE.md) for the
authoritative lock and **YES** to begin J1.0 implementation.

---

## 1. Recommended architecture

```text
User Request (natural language)
        │
        ▼
AI Copilot
(independent bounded context · conversation / explanation orchestration)
        │
        │  cites / navigates / explains — never recalculates
        ▼
┌─────────────────────────────────────────────────────┐
│  Analysis · DI · IEF · Comparison · Portfolio       │
│  Qualitative Risk · Research · Quantitative Risk    │
│  Recommendation · Workflow · Knowledge Graph        │
│  (immutable reports + refs only — never owned)      │
└─────────────────────────────────────────────────────┘
        │
        ▼
    CopilotResponse
```

**Not a replacement for any frozen owner:**

```text
Frozen domains answer:     "What is true / what is the posture / what to do /
                            how did execution happen / how is it connected?"
AI Copilot answers:        "How do I explain those results to the user in
                            natural language, with evidence and traceability?"
```

```text
Frozen domain packages + Knowledge Graph
        ▲
        │ public façades / report citations only (one-way)
        │
packages/copilot/   ← proposed
        │
        ├── CopilotIdentity / CopilotProfile
        ├── ConversationSession / ConversationTurn
        ├── ConversationContext / ContextBundle
        ├── UserIntent / Explanation
        ├── CopilotSummary / CopilotMetadata
        │
        ▼
   CopilotResponse

dsp_platform → additive re-exports only
LLM providers → adapters outside domain (OpenAI / Anthropic / Gemini / local)
```

**Canonical pipeline (proposed for J1.x):**

```text
User Request
        │
        ▼
Conversation Engine     (intent · routing · session turns)
        │
        ▼
Context Builder         (assemble ContextBundle from citations)
        │
        ▼
Knowledge Graph         (navigate connections — cite KnowledgeGraphReport)
        │
        ▼
Explanation Engine      (evidence-backed Explanation artifacts)
        │
        ▼
Copilot Reporter        (presentation only)
        │
        ▼
CopilotResponse
```

Baseline already reserves **Epic J** as “LLM / agent adapters over frozen
reports; domain remains LLM-agnostic” — this design affirms that pattern.

---

## 2. Design questions — decisions

### Q1 — Independent bounded context?

**Yes — independent bounded context.**

| Option | Verdict |
|---|---|
| Fold into Knowledge Graph (`packages/knowledge_graph/`) | **Reject** — KG owns relationships / lineage (I1.4); conversation would violate freeze |
| Fold into Workflow | **Reject** — Workflow owns execution lifecycle (H1.4) |
| Fold into Recommendation | **Reject** — Recommendation owns action synthesis (G1.4) |
| Fold into `dsp_platform` only | **Reject** — needs stable domain contracts and ownership |
| Embed as OpenAI / Anthropic product SDK in domain | **Reject for domain** — adapters may exist later; domain is LLM-agnostic contracts |
| Independent AI Copilot package | **Accept** |

**Rationale:**

1. Baseline v1.0 already reserves **Epic J** for conversational / agent access
   **outside** analysis and orchestration ownership.  
2. Frozen subsystems must remain pure owners of their reports; Copilot
   **orchestrates explanation** across them.  
3. Knowledge Graph must not absorb conversation memory / intent routing as a
   second identity.  
4. Future UI / API / chat surfaces need a stable `CopilotResponse` without
   owning business engines, workflows, or graph construction.  
5. LLM providers change; domain contracts must not.

---

### Q2 — What should AI Copilot own?

| Artifact | Own? | Notes |
|---|---|---|
| `CopilotIdentity` | **Yes** | Copilot run / assistant / tenant identity |
| `ConversationSession` | **Yes** | Ordered conversation lifecycle container |
| `ConversationTurn` | **Yes** | Immutable user / assistant turn record |
| `ConversationContext` | **Yes** | Active session scope (as-of, focus entity, constraints) |
| `UserIntent` | **Yes** | Structured intent classification (route target — not a market conclusion) |
| `ContextBundle` | **Yes** | Assembled citation pack for one turn / explanation |
| `Explanation` | **Yes** | Evidence-backed narrative / structured explanation artifact |
| `CopilotProfile` | **Yes** | Aggregate root — cites upstream reports; owns conversation artifacts only |
| `CopilotResponse` | **Yes** | Canonical immutable presentation / chat response snapshot |
| `CopilotMetadata` | **Yes** | Model-agnostic run metadata (as-of, owner, tags, limitations) |
| `CopilotSummary` | **Yes** (recommended) | Counts / coverage / limitations for the response |

**Supporting (citation-only):** local references to Analysis / Decision /
Evidence / Comparison / Portfolio / Risk / Research / Quant / Recommendation /
Workflow / Knowledge Graph outcomes — **never** embedded report payloads.

**Supporting (ports — not ownership of providers):**

| Port (design) | Role |
|---|---|
| `LanguageModelPort` | Adapter-facing generation / classification only |
| `CitationResolverPort` (optional) | Resolve public façade / report digests for Context Builder |

Suggested intent classes (design — freeze in J0.0A):

| Intent class | Routes toward |
|---|---|
| `EXPLAIN_REPORT` | Explain a cited upstream report |
| `NAVIGATE_GRAPH` | Knowledge Graph navigation / lineage questions |
| `SUMMARIZE_POSTURE` | Summarize Decision / Risk / Recommendation citations |
| `TRACE_EVIDENCE` | Evidence aggregation / EvidenceLink walk (cite-only) |
| `COMPARE_OUTCOMES` | Present Comparison / multi-report contrasts |
| `CLARIFY` / `UNKNOWN` | Clarifying questions / out-of-scope refusal |

Intent classes **must never** encode BUY / SELL / HOLD as domain conclusions —
those remain Recommendation ownership when present as citations.

---

### Q3 — What must it NEVER own?

| Forbidden ownership | Why |
|---|---|
| Business analysis engines | Belong to Analysis / DI / IEF / Comparison |
| Intrinsic value / valuation math | Valuation / Analysis freezes |
| Portfolio construction / monitoring | Portfolio freeze |
| Risk calculation (qual or quant) | Risk / Quant freezes |
| Recommendation options / scores | Recommendation freeze |
| Workflow state machines / orchestration | Workflow freeze |
| Knowledge Graph topology / lineage construction | Knowledge Graph freeze |
| Market data series | Data engine / providers |
| Trading / OMS / optimization | Future external epics |
| Persistence / chat stores as domain core | Infrastructure adapters |
| Vendor LLM SDKs (OpenAI, Anthropic, Gemini, …) | Optional future adapters — not domain core |

**No ownership leakage allowed.**

---

### Q4 — Which frozen bounded contexts should it consume?

| Upstream context | Consume? | Mode |
|---|---|---|
| Analysis Framework | **Yes** | Reference / digest citation |
| Decision Intelligence | **Yes** | Reference only |
| Industry Evidence | **Yes** | Reference only |
| Comparison | **Yes** | Reference only |
| Portfolio | **Yes** | Reference only |
| Qualitative Risk | **Yes** | Reference only |
| Research | **Yes** | Reference only |
| Quantitative Risk | **Yes** | Reference only |
| Recommendation | **Yes** | Reference only |
| Workflow | **Yes** | Reference only (execution audit / status) |
| Knowledge Graph | **Yes** | Primary navigation / lineage citation (`KnowledgeGraphReport`) |

**Policy:** consume **immutable reports only**. Never reopen upstream engines to
recalculate. Never rewrite upstream reports. Missing reports → limitations /
incomplete explanation — never invent financial conclusions to “fill gaps.”

J0.0A should lock which refs are **required vs optional** per profile (e.g.
graph-navigation session vs recommendation-explanation session).

**Default design lean:** Knowledge Graph citation **strongly preferred** for
navigation / “why connected?” turns; Recommendation + Workflow + Risk often
required for action / execution / posture explanations.

---

### Q5 — Responsibilities

| Responsibility | In scope? | Notes |
|---|---|---|
| Intent detection | **Yes** | Structured `UserIntent` — domain or adapter-assisted via port |
| Conversation routing | **Yes** | Route to explanation / navigation / clarify paths |
| Context assembly | **Yes** | Build `ContextBundle` from citations |
| Knowledge Graph navigation | **Yes** | Cite / present KG connections — never construct graph |
| Explanation generation | **Yes** | Produce `Explanation` from ContextBundle + (optional) LLM port |
| Evidence aggregation | **Yes** | Collect cite-backed evidence refs into response |
| Conversation memory | **Yes** | Session / turn artifacts in domain; durable store outside |
| Citation handling | **Yes** | Digests / report ids / provenance on every claim |
| Traceability | **Yes** | Link response claims → ContextBundle → upstream digests |
| Financial calculations | **No** | Never compute metrics / valuations / risk numbers |
| Recommendation generation | **No** | Cite RecommendationReport only |
| Workflow execution | **No** | Never invoke WorkflowEngine |
| Graph construction | **No** | Never invoke KnowledgeGraphEngine |

---

### Q6 — What remains outside?

| Outside | Owner |
|---|---|
| Financial / intrinsic-value calculations | Frozen analysis / valuation domains |
| Risk calculations | Risk / Quantitative Risk |
| Recommendation generation | Recommendation (G) |
| Workflow execution / retries / gates | Workflow (H) |
| Knowledge Graph construction | Knowledge Graph (I) |
| Persistence / chat history databases | Infrastructure adapters |
| Vendor LLM SDKs / streaming transport | Adapters implementing `LanguageModelPort` |
| Optimization / OMS / trading | Future Optimizer / OMS |
| UI rendering / voice / channel adapters | Application layer |

---

### Q7 — Relationship with Knowledge Graph

| Subsystem | Answers |
|---|---|
| **Knowledge Graph** | “How are platform entities, reports, and evidence connected?” |
| **AI Copilot** | “How do I explain those connections (and other frozen results) to the user?” |

```text
KnowledgeGraphReport ──cited──► AI Copilot  (navigation / lineage explanations)
CopilotResponse       ──✕──► Knowledge Graph domain  (no reverse import)

Recommendation  →  "What should be done?"
Workflow        →  "In what order and under what conditions?"
Knowledge Graph →  "How is everything connected / traceable?"
AI Copilot      →  "How do we explain / navigate in natural language?"
```

Knowledge Graph remains the **relationship / lineage index**. AI Copilot
remains the **conversation / explanation orchestrator**. Neither absorbs the
other’s ownership.

---

## 3. Architectural principles

| Principle | Meaning |
|---|---|
| Single ownership | Upstream aggregates stay owned by frozen domains |
| Reference-only integration | Digests / ids / status / version only |
| Immutable inputs | Consume frozen reports; never mutate them |
| Conversation orchestration | Session / turn / intent / context — not analysis |
| Explainability-first | Citations + EvidenceLink / Lineage navigation required |
| No ownership leakage | Never absorb business facts or engines |
| LLM-agnostic domain | No direct provider dependency; ports + adapters only |
| Additive extension | New intents / channels / models — no redesign |

---

## 4. LLM policy (design)

The domain **SHALL NOT** depend directly on any LLM provider.

```text
copilot domain
    │
    │  LanguageModelPort (local port — no vendor types)
    ▼
adapters (outside)
    ├── OpenAI
    ├── Anthropic
    ├── Google Gemini
    └── Local models
```

| Rule | Status (design) |
|---|---|
| Domain contracts free of provider SDKs | **Required** |
| Adapter swap without domain contract change | **Required** |
| Deterministic / stub adapters for tests | **Required** |
| LLM optional for some intents (template / structured explanation) | **Allowed** |
| Silent invention of missing financial facts | **Forbidden** |

J0.0A must freeze the port surface (inputs / outputs / error classes) and the
refusal policy for out-of-scope financial questions.

---

## 5. Dependencies (proposed)

```text
copilot ──depends──► core
copilot ──cites──► frozen report outcomes (refs only)
copilot ──cites──► KnowledgeGraphReport (navigation)
adapters (outside) ──implement──► LanguageModelPort
adapters (outside) ──may read──► upstream public façades
upstream domains ──✕──► copilot
knowledge_graph ──✕──► copilot   (unless additive consumer later outside)
```

**Allowed:** `core` (+ stdlib).  
**Forbidden in domain:** OpenAI / Anthropic / Gemini / local-runtime SDKs,
orchestration engines, recommendation / risk / research / portfolio engines,
Neo4j / persistence drivers, WorkflowEngine / KnowledgeGraphEngine invocation
as owned logic.

---

## 6. Proposed package & roadmap

| Phase | Scope | Status |
|---|---|---|
| **J0.0** | Architecture design (this document) | **DONE** |
| **J0.0A** | Architecture freeze | **DONE / FROZEN** · see [J0.0A](J0_0A_AI_COPILOT_ARCHITECTURE_FREEZE.md) |
| **J1.0** | Domain models in `packages/copilot/` (proposed name) | **DONE** ([J1.0](J1_0_AI_COPILOT_DOMAIN_MODELS.md)) |
| **J1.1** | Assembler / Context Builder | **DONE** ([J1.1](J1_1_AI_COPILOT_CONVERSATION_ENGINE.md)) |
| **J1.2** | Conversation / Explanation Engine (+ LLM port) | **DONE** ([J1.2](J1_2_AI_COPILOT_EXPLANATION_ENGINE.md)) |
| **J1.3** | Reporter (`CopilotResponse`) | **DONE** · see [J1.3](J1_3_AI_COPILOT_REPORTER.md) |
| **J1.4** | Validation & freeze | **DONE / FROZEN** · see [J1.4](J1_4_AI_COPILOT_VALIDATION_FREEZE.md) |

**Proposed package name:** `packages/copilot/` (lock in J0.0A; alternatives
`ai_copilot` / `assistant` rejected unless freeze chooses otherwise).

**Pipeline (proposed):** Models → Assembler/Context Builder → Conversation /
Explanation Engine → Reporter → `CopilotResponse`.

---

## 7. Non-goals (this phase)

- No packages, models, or code  
- No financial calculations  
- No recommendation / risk / workflow / graph engines  
- No persistence  
- No vendor LLM SDKs inside the domain  
- No redesign of frozen Qualitative / Quant / Recommendation / Workflow /
  Knowledge Graph stacks  

---

## 8. Conditions for J0.0A (must lock)

1. Package name (`packages/copilot/` recommended).  
2. Ownership list for conversation / explanation artifacts (Q2).  
3. Forbidden ownership list (Q3) — especially “never owns Knowledge Graph.”  
4. `LanguageModelPort` boundary and refusal / hallucination policy.  
5. Required vs optional upstream citations per Copilot profile.  
6. Conversation memory: domain session/turn vs durable store adapters.  
7. Canonical pipeline naming (Conversation Engine / Context Builder /
   Explanation Engine / Reporter).  
8. No reverse imports; deps ⊆ `{core}`; additive `dsp_platform` re-exports.  
9. Intent taxonomy (additive-only after freeze).  
10. Explicit non-goals: no BUY/SELL/HOLD invention; no engine re-execution.

---

## 9. PASS / FAIL

**PASS** — AI Copilot architecture is sufficiently designed for J0.0A freeze.

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | **AI Copilot architecture design (J0.0)** |
| [I1_4_KNOWLEDGE_GRAPH_VALIDATION_AND_FREEZE.md](I1_4_KNOWLEDGE_GRAPH_VALIDATION_AND_FREEZE.md) | Knowledge Graph freeze |
| [H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md](H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md) | Workflow freeze |
| [G1_4_RECOMMENDATION_VALIDATION_AND_FREEZE.md](G1_4_RECOMMENDATION_VALIDATION_AND_FREEZE.md) | Recommendation freeze |
| [DSP_ARCHITECTURE_BASELINE_v1_0.md](DSP_ARCHITECTURE_BASELINE_v1_0.md) | Platform baseline |

---

## Final question

Is the AI Copilot sufficiently well-defined to become the next bounded context
of the DSP AI Indicator platform?

**YES WITH CONDITIONS**
