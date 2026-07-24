# Phase I0.0 — Knowledge Graph Architecture & Design

**Status:** Design review complete · **Superseded on conflicts by** [I0.0A Architecture Freeze](I0_0A_KNOWLEDGE_GRAPH_ARCHITECTURE_FREEZE.md)  
**Prerequisite:** [DSP Architecture Baseline v1.0](DSP_ARCHITECTURE_BASELINE_v1_0.md) · Qualitative stack frozen · Quantitative Risk **E2.4 FROZEN** · Recommendation **G1.4 FROZEN** · Workflow **H1.4 FROZEN**  
**Suite gate:** **1385 / 1385** passing (2026-07-21)

## Verdict

**YES WITH CONDITIONS** (at design time) — conditions satisfied by I0.0A freeze.
See [I0.0A](I0_0A_KNOWLEDGE_GRAPH_ARCHITECTURE_FREEZE.md) for the
authoritative lock and **YES** to begin I1.0 implementation.

---

## 1. Recommended architecture

```text
Frozen bounded contexts (immutable reports)
  Analysis · DI · IEF · Comparison · Portfolio
  Qualitative Risk · Research · Quantitative Risk
  Recommendation · Workflow
        │
        │  citations / digests / ids / status only
        ▼
Knowledge Graph
(independent bounded context · relationship index)
        │
        ├── GraphIdentity / GraphProfile
        ├── GraphNode / GraphEdge / GraphRelationship
        ├── EvidenceLink / Lineage
        ├── GraphSummary
        │
        ▼
KnowledgeGraphReport
```

**Not a replacement for any frozen owner:**

```text
Frozen domains answer:     "What is true / what is the posture / what to do /
                            how did execution happen?"
Knowledge Graph answers:   "How are entities, reports, evidence, and
                            executions connected across the platform?"
```

```text
Frozen domain packages
        ▲
        │ public façades / report citations only (one-way)
        │
packages/knowledge_graph/   ← proposed
        │
        ├── GraphIdentity / Profile
        ├── GraphNode / GraphEdge / GraphRelationship
        ├── EvidenceLink / Lineage
        ├── GraphSummary
        │
        ▼
   KnowledgeGraphReport

dsp_platform → additive re-exports only
```

**Canonical pipeline (proposed for I1.x):**

```text
Immutable Domain Models
        │
        ▼
Graph Assembler   (normalize nodes / edges / citations / lineage)
        │
        ▼
Graph Engine      (deterministic relationship / lineage assembly)
        │
        ▼
Graph Reporter    (presentation / navigation aids only)
        │
        ▼
KnowledgeGraphReport
```

Baseline already reserves **Epic I** as “Index / link citations; not a new
owner of upstream aggregates” — this design affirms that pattern.

---

## 2. Design questions — decisions

### Q1 — Independent bounded context?

**Yes — independent bounded context.**

| Option | Verdict |
|---|---|
| Fold into Workflow (`packages/workflow/`) | **Reject** — Workflow owns execution lifecycle (H1.4); graph would violate freeze |
| Fold into Recommendation | **Reject** — Recommendation owns action synthesis (G1.4) |
| Fold into Research | **Reject** — Research owns investigation synthesis (F1.4) |
| Fold into `dsp_platform` only | **Reject** — needs stable domain contracts and ownership |
| Embed as Neo4j / vendor graph product | **Reject for domain** — adapters may exist later; domain is immutable contracts |
| Independent Knowledge Graph package | **Accept** |

**Rationale:**

1. Baseline v1.0 already reserves **Epic I** for citation / link indexing
   **outside** analysis and orchestration ownership.  
2. Frozen subsystems must remain pure owners of their reports; the graph
   **indexes relationships** among them.  
3. Workflow must not absorb cross-domain navigation / evidence lineage as a
   second identity.  
4. Future Copilot / UI / audit tools need a stable `KnowledgeGraphReport`
   without owning business engines or execution.

---

### Q2 — What should Knowledge Graph own?

| Artifact | Own? | Notes |
|---|---|---|
| `GraphIdentity` | **Yes** | Graph build / session / corpus identity |
| `GraphProfile` | **Yes** | Aggregate root — cites upstream reports; owns graph artifacts only |
| `GraphNode` | **Yes** | Entity / report / evidence / execution / instrument node (typed) |
| `GraphEdge` | **Yes** | Directed connection between nodes (typed) |
| `GraphRelationship` | **Yes** | Named relationship descriptor (kind, role, constraints) |
| `EvidenceLink` | **Yes** | Cite-backed link from claim / node to evidence / report digests |
| `Lineage` | **Yes** | Ordered provenance chain (report → report, execution → outcome) |
| `GraphSummary` | **Yes** | Counts / coverage / limitations |
| `KnowledgeGraphReport` | **Yes** | Canonical immutable presentation / navigation snapshot |

**Supporting (citation-only):** local references to Analysis / Decision /
Evidence / Comparison / Portfolio / Risk / Research / Quant / Recommendation /
Workflow outcomes — **never** embedded report payloads.

**Suggested node kinds (design — freeze in I0.0A):**

| Kind | Examples |
|---|---|
| Entity | Instrument, portfolio, industry / universe entry |
| Report | Upstream report identity + digest citation |
| Evidence | Evidence bundle / observation citation |
| Execution | Workflow execution / step attempt citation |
| Capability | Declared subsystem / façade capability (optional) |

**Suggested relationship kinds (design — freeze in I0.0A):**

| Kind | Meaning |
|---|---|
| `CITES` | Node cites upstream report / evidence |
| `DERIVED_FROM` | Report / score derived from cited inputs |
| `PRODUCED_BY` | Outcome produced by workflow execution / step |
| `DEPENDS_ON` | Prerequisite / dependency edge |
| `SUPPORTS` / `CONFLICTS_WITH` | Evidence / research posture links (cite-only) |
| `PART_OF` | Membership (instrument ∈ portfolio, etc.) |

---

### Q3 — What must it NEVER own?

| Forbidden ownership | Why |
|---|---|
| Business analysis engines | Belong to Analysis / DI / IEF / Comparison |
| Portfolio construction / monitoring engines | Portfolio freeze |
| Risk calculation (qual or quant) | Risk / Quant freezes |
| Recommendation options / scores | Recommendation freeze |
| Workflow state machines / orchestration | Workflow freeze |
| Market data series | Data engine / providers |
| Trading / OMS / optimization | Future external epics |
| Schedulers / queues / persistence | Infrastructure adapters |
| Graph database products (Neo4j, etc.) | Optional future adapters — not domain core |
| LLM reasoning / embeddings as required core | Copilot epic / adapters |

**No ownership leakage allowed.**

---

### Q4 — Which frozen reports should it consume?

| Upstream output | Consume? | Mode |
|---|---|---|
| Analysis Framework outcomes | **Yes** | Reference / digest citation |
| DecisionPack / Decision report | **Yes** | Reference only |
| Industry Evidence / EvidenceBundle | **Yes** | Reference only |
| ComparisonReport | **Yes** | Reference only |
| Portfolio / monitoring outcomes | **Yes** | Reference only |
| Qualitative RiskReport | **Yes** | Reference only |
| ResearchReport | **Yes** | Reference only |
| QuantitativeRiskReport | **Yes** | Reference only |
| RecommendationReport | **Yes** | Reference only |
| WorkflowReport | **Yes** | Reference only (execution lineage) |

**Policy:** consume **immutable reports only**. Never reopen upstream engines.
Never rewrite upstream reports. Missing reports → limitations / incomplete
coverage — never invent nodes to “fill gaps.”

I0.0A should lock which refs are **required vs optional** per graph profile
(e.g. investigation graph vs full-platform corpus graph).

---

### Q5 — Responsibilities

| Responsibility | In scope? | Notes |
|---|---|---|
| Graph construction | **Yes** | Assembler / Engine build nodes + edges from citations |
| Relationship management | **Yes** | Typed edges / relationships; no business scoring |
| Evidence linkage | **Yes** | `EvidenceLink` cite-backed |
| Report lineage | **Yes** | Report → report / report → evidence chains |
| Execution lineage | **Yes** | Workflow execution → outcome citations |
| Dependency graph | **Yes** | Prerequisites / depends-on among steps / reports |
| Entity navigation | **Yes** | Presentational navigation aids on report |
| Traceability / explainability support | **Yes** | Lineage + citations for Copilot / UI / audit |
| Business conclusions | **No** | Never compute BUY/SELL/HOLD or risk metrics |
| Workflow execution | **No** | Invoke nothing; cite WorkflowReport only |

---

### Q6 — What remains outside?

| Outside | Owner |
|---|---|
| Business logic / primary analysis | Frozen qualitative / quantitative domains |
| Recommendations | Recommendation (G) |
| Risk calculation | Risk / Quantitative Risk |
| Workflow execution / retries / gates | Workflow (H) |
| Scheduling / queues / persistence | Infrastructure adapters |
| Optimization / OMS / trading | Future Optimizer / OMS |
| LLM reasoning / RAG stores | Copilot (J) / adapters |
| Graph DB / Cypher / SPARQL engines | Optional future adapters |
| Full-text / vector search products | Outside domain |

---

### Q7 — Relationship with Workflow

| Subsystem | Answers |
|---|---|
| **Workflow** | “How did execution happen?” (order, state, retries, audit) |
| **Knowledge Graph** | “How are all platform entities, reports, and evidence connected?” |

```text
WorkflowReport ──cited──► Knowledge Graph  (execution lineage nodes/edges)
KnowledgeGraphReport ──✕──► Workflow domain  (no reverse import)

Recommendation  →  "What should be done?"
Workflow        →  "In what order and under what conditions?"
Knowledge Graph →  "How is everything connected / traceable?"
Copilot (future)→  "How do we explain / navigate in natural language?"
```

Workflow remains the **process conductor**. Knowledge Graph remains the
**relationship / lineage index**. Neither absorbs the other’s ownership.

---

## 3. Architectural principles

| Principle | Meaning |
|---|---|
| Single ownership | Upstream aggregates stay owned by frozen domains |
| Reference-only integration | Digests / ids / status / version only |
| Immutable graph | Frozen dataclasses; new builds emit new reports |
| No reverse imports | Upstream packages never import Knowledge Graph |
| No business calculations | No scores, rankings, risk math, or recommendations |
| Explainability-first | Lineage + EvidenceLink are first-class |
| Façade / citation discipline | Public report façades or local refs — no deep engine imports |
| Additive extension | Parallel graphs, richer taxonomies, adapters — no redesign |

---

## 4. Dependencies (proposed)

```text
knowledge_graph ──depends──► core
knowledge_graph ──cites──► frozen report outcomes (refs only)
adapters (optional, outside) ──may read──► upstream public façades
upstream domains ──✕──► knowledge_graph
workflow / recommendation ──✕──► knowledge_graph   (unless additive
                                                      consumer later outside)
```

**Allowed:** `core` (+ stdlib).  
**Forbidden in domain:** Neo4j / graph DB SDKs, orchestration, recommendation,
risk, research, portfolio engines, LLM SDKs, persistence drivers.

---

## 5. Proposed package & roadmap

| Phase | Scope | Status |
|---|---|---|
| **I0.0** | Architecture & design (this document) | **DONE** |
| **I0.0A** | Architecture freeze | **DONE / FROZEN** · see [I0.0A](I0_0A_KNOWLEDGE_GRAPH_ARCHITECTURE_FREEZE.md) |
| **I1.0** | Domain models in `packages/knowledge_graph/` | **DONE** · see [I1.0](I1_0_KNOWLEDGE_GRAPH_DOMAIN_MODELS.md) |
| **I1.1** | Assembler (node / edge / citation bind) | **DONE** · see [I1.1](I1_1_KNOWLEDGE_GRAPH_ASSEMBLER.md) |
| **I1.2** | Graph Engine (deterministic relationship / lineage assembly) | **DONE** ([I1.2](I1_2_KNOWLEDGE_GRAPH_ENGINE.md)) |
| **I1.3** | Reporter (`KnowledgeGraphReport`) | **DONE** ([I1.3](I1_3_KNOWLEDGE_GRAPH_REPORTER.md)) |
| **I1.4** | Validation & freeze | **DONE / FROZEN** ([I1.4](I1_4_KNOWLEDGE_GRAPH_VALIDATION_AND_FREEZE.md)) |

**I0.0A must freeze:** package name, ownership list, required/optional report
set, node/edge/relationship taxonomy, lineage shape, pipeline
(Models → Assembler → Engine → Reporter), and non-goals (no graph DB in
domain).

---

## 6. Non-goals (this phase and early I1.x)

- Graph database products (Neo4j, etc.)  
- Persistence / query engines in domain core  
- Implementation / packages / models (I0.0)  
- Business analysis / recommendations / risk math  
- Workflow execution / scheduling  
- Optimization / OMS / trading  
- LLM / embedding-required core paths  

---

## 7. Known open points (for I0.0A)

1. Exact required vs optional upstream report set per profile.  
2. Canonical node id scheme (`kind:id` vs opaque digests).  
3. Whether `GraphRelationship` is distinct from `GraphEdge` or a view.  
4. Depth of Workflow execution lineage (report-level vs per-step).  
5. Whether multi-graph corpora (per investigation vs platform-wide) need
   separate identity namespaces.  
6. Adapter placement for optional future graph-DB projection.

---

## 8. PASS / FAIL

**PASS** — Knowledge Graph architecture is sufficiently designed for
**I0.0A Architecture Freeze**.

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | Knowledge Graph design (I0.0) |
| [I0_0A_KNOWLEDGE_GRAPH_ARCHITECTURE_FREEZE.md](I0_0A_KNOWLEDGE_GRAPH_ARCHITECTURE_FREEZE.md) | **Authoritative architecture freeze** |
| [DSP_ARCHITECTURE_BASELINE_v1_0.md](DSP_ARCHITECTURE_BASELINE_v1_0.md) | Platform baseline (Epic I reserved) |
| [H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md](H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md) | Workflow freeze |
| [G1_4_RECOMMENDATION_VALIDATION_AND_FREEZE.md](G1_4_RECOMMENDATION_VALIDATION_AND_FREEZE.md) | Recommendation freeze |
| [E2_4_QUANTITATIVE_RISK_VALIDATION_AND_FREEZE.md](E2_4_QUANTITATIVE_RISK_VALIDATION_AND_FREEZE.md) | Quant freeze |

---

## Final question

Is Knowledge Graph sufficiently well-defined to become the next bounded
context of the DSP AI Indicator platform?

**YES** — architecture frozen in [I0.0A](I0_0A_KNOWLEDGE_GRAPH_ARCHITECTURE_FREEZE.md).
