# Phase I0.0A — Knowledge Graph Architecture Freeze

**Status:** **FROZEN**  
**Date:** 2026-07-21  
**Preceded by:** [I0.0 Knowledge Graph Design](I0_0_KNOWLEDGE_GRAPH_DESIGN.md)  
**Prerequisite:** [DSP Architecture Baseline v1.0](DSP_ARCHITECTURE_BASELINE_v1_0.md) · Qualitative stack frozen · Quantitative Risk E2.4 frozen · Recommendation G1.4 frozen · Workflow H1.4 frozen · **1385 tests green**  
**This phase:** Architecture lock only — **no code, no packages, no package modifications**

---

## Freeze declaration

The following are **authoritative** until an explicit freeze amendment:

1. Knowledge Graph is an **independent bounded context**.  
2. Target package: **`packages/knowledge_graph/`** (create in I1.0).  
3. Knowledge Graph owns **only** the artifacts listed in §3.  
4. Knowledge Graph **indexes relationships / lineage only** — never performs
   business analysis and never owns business facts.  
5. Interaction with frozen subsystems is **public façade / local reference only** —
   immutable reports and reference metadata only; no deep engine / assembler /
   reporter imports from upstream domains.  
6. No reverse imports into Analysis / DI / IEF / Comparison / Portfolio / Risk /
   Research / Quant / Recommendation / Workflow.  
7. Pipeline is frozen as **Models → KnowledgeGraphAssembler →
   KnowledgeGraphEngine → KnowledgeGraphReporter → KnowledgeGraphReport**.  
8. Node / relationship / evidence-link / lineage taxonomies are frozen in §5.  
9. Report consumption policy (required vs optional) is frozen in §6.  
10. Persistence, graph databases, query engines, schedulers, and LLM reasoning
    live **outside** the domain (adapters only).

Conflicts with this document lose unless a later dated freeze amendment
supersedes them. On conflicts with I0.0 design prose, **this freeze wins**.

---

## 1. Architecture validation

```text
Knowledge Graph (packages/knowledge_graph/)
        │
        │  nodes / edges / evidence links / lineage
        ▼
┌─────────────────────────────────────────────────────┐
│  Analysis · DI · IEF · Comparison · Portfolio       │
│  Qualitative Risk · Research · Quant · Recommend.   │
│  Workflow                                           │
│  (immutable reports + refs only — never owned)      │
└─────────────────────────────────────────────────────┘
        │
        ▼
    KnowledgeGraphReport
```

**Canonical pipeline (frozen):**

```text
Immutable Domain Models
        │
        ▼
KnowledgeGraphAssembler   (normalize nodes / edges / citations / lineage)
        │
        ▼
KnowledgeGraphEngine      (deterministic relationship / lineage assembly)
        │
        ▼
KnowledgeGraphReporter    (presentation / navigation aids only)
        │
        ▼
KnowledgeGraphReport
```

| Knowledge Graph **is** | Knowledge Graph **is not** |
|---|---|
| Independent DSP bounded context | An extension of Workflow or Recommendation |
| Relationship / lineage index | Business analysis engine |
| Producer of `KnowledgeGraphReport` | Owner of Decision / Risk / Recommendation / Workflow facts |
| Cite-only consumer of frozen reports | Deep importer of upstream engines |
| Explainability / traceability support | Graph database / persistence / query product |

**Sibling relationships (frozen):**

```text
Recommendation  →  "What should be done?"
Workflow        →  "In what order and under what conditions
                    should capabilities execute?"
Knowledge Graph →  "How are entities, reports, evidence,
                    and executions connected?"
Optimizer/OMS   →  "How do we search / place orders?" (future, external)
Copilot         →  "How do we explain / navigate in language?"
```

### Boundary one-liners (frozen)

| Subsystem | Answers |
|---|---|
| Frozen analysis domains | “What is true / what is the posture?” |
| **Recommendation** | “What should be done?” |
| **Workflow** | “How did execution happen?” |
| **Knowledge Graph** | “How are all platform entities, reports, and evidence connected?” |
| Optimizer / OMS (future) | “How do we search / execute trades?” |
| **AI Copilot** | “How do we explain this in natural language?” · see [J0.0A](J0_0A_AI_COPILOT_ARCHITECTURE_FREEZE.md) |

**Architecture validation:** **PASS**

---

## 2. Ownership matrix

| Domain | Owns | Knowledge Graph relationship |
|---|---|---|
| **Knowledge Graph** | Artifacts in §3 | Relationship / lineage ownership only |
| **Frozen upstream domains** | Their reports / engines | Cited via refs; never owned |
| **Infrastructure adapters** | Graph DB, storage, search, viz | Outside domain |
| **Copilot / UI** | Presentation / LLM adapters | Consume `KnowledgeGraphReport` externally |

### Knowledge Graph owns ONLY

| Artifact | Role |
|---|---|
| `GraphIdentity` | Graph build / session / corpus identity |
| `GraphProfile` | Aggregate root |
| `GraphNode` | Typed graph vertex |
| `GraphEdge` | Directed typed connection |
| `GraphRelationship` | Named relationship descriptor |
| `EvidenceLink` | Cite-backed evidence association |
| `Lineage` | Ordered provenance chain |
| `GraphSummary` | Counts / coverage / limitations |
| `KnowledgeGraphReport` | Canonical immutable presentation / navigation snapshot |

Supporting (not upstream ownership): local report references, Assembler /
Engine / Reporter context·result·status types, taxonomy enums.

### Knowledge Graph owns NONE of

Analysis · Decision · Industry Evidence · Comparison · Portfolio · Risk ·
Research · Quantitative Risk · Recommendation · Workflow · Market Data ·
Trading · OMS · Persistence · Graph Database products.

**No ownership leakage.** Ownership validation: **PASS**

---

## 3. Dependency graph

```text
knowledge_graph ──depends──► core
knowledge_graph ──cites──► immutable report outcomes (refs / metadata only)
adapters (outside) ──may read──► upstream public façades
adapters (outside) ──may project──► graph DB / search / viz
upstream domains ──✕──► knowledge_graph
```

### Frozen dependency rules

Knowledge Graph **SHALL**:

- Consume immutable reports only  
- Consume reference metadata only (ids, digests, versions, status, timestamps)  
- Interact through public façades only (or local refs derived from reports)  
- Never import subsystem internals (`engine` / `assembler` / `reporter` modules)  
- Never create reverse imports  
- Never create dependency cycles  
- Never embed vendor graph-DB / LLM / persistence SDKs in domain core  

**Allowed runtime deps (I1.0+):** ⊆ `{core}` (+ stdlib).  

Dependency validation: **PASS**

---

## 4. Responsibilities

### Knowledge Graph SHALL

- Construct graph objects (`GraphNode`, `GraphEdge`, …)  
- Maintain typed relationships  
- Link evidence (`EvidenceLink`)  
- Maintain report lineage  
- Maintain execution lineage (from `WorkflowReport` citations)  
- Support dependency tracing  
- Support explainability  
- Provide `GraphSummary` / `KnowledgeGraphReport`  

### Knowledge Graph SHALL NEVER

- Calculate financial metrics  
- Generate recommendations  
- Execute workflows  
- Schedule jobs  
- Persist graph data  
- Perform graph database operations  
- Embed LLM reasoning as required core behavior  
- Rewrite upstream reports  

---

## 5. Taxonomy (frozen)

Future additions to taxonomy **SHALL be additive only** (new enum members /
optional fields). Renaming or removing frozen members requires freeze amendment.

### Node categories (frozen)

| Category | Role |
|---|---|
| `COMPANY` | Issuer / company entity |
| `SECURITY` | Tradable instrument / security |
| `PORTFOLIO` | Portfolio entity citation |
| `REPORT` | Upstream report citation node |
| `EVIDENCE` | Evidence / observation citation node |
| `WORKFLOW` | Workflow / execution citation node |
| `RECOMMENDATION` | Recommendation citation node |
| `RISK` | Risk report / posture citation node |
| `RESEARCH` | Research citation node |
| `ENTITY` | Generic / catch-all entity node |

### Relationship categories (frozen)

| Category | Meaning |
|---|---|
| `REFERENCES` | Node references another report / entity |
| `DERIVES_FROM` | Derived from cited inputs |
| `DEPENDS_ON` | Prerequisite / dependency |
| `SUPPORTED_BY` | Supported by evidence / research |
| `GENERATED_BY` | Produced by a capability / report process |
| `EXECUTED_BY` | Tied to workflow execution |
| `RELATED_TO` | Generic undirected-style association (still recorded as directed edge + notes) |

### Evidence link categories (frozen)

| Category | Meaning |
|---|---|
| `DIRECT` | Direct citation to evidence / report |
| `INDIRECT` | Indirect / transitive citation |
| `DERIVED` | Derived association from cited lineage |

### Lineage categories (frozen)

| Category | Meaning |
|---|---|
| `REPORT` | Report → report / report → evidence chains |
| `EXECUTION` | Workflow execution → outcome chains |
| `EVIDENCE` | Evidence observation / bundle chains |

Taxonomy validation: **PASS**

---

## 6. Report policy (frozen)

Knowledge Graph consumes **immutable reports only**. Missing optional reports
yield limitations / incomplete coverage — never invent upstream facts.

### Required

| Report | Role |
|---|---|
| `RecommendationReport` | Action-posture citation anchor |
| `WorkflowReport` | Execution lineage anchor |

### Optional

| Report | Role |
|---|---|
| Analysis Framework outcomes | Analysis citation |
| DecisionPack / Decision report | Decision citation |
| Industry Evidence / EvidenceBundle | Evidence citation |
| `ComparisonReport` | Comparison citation |
| Portfolio / monitoring outcomes | Portfolio citation |
| Qualitative `RiskReport` | Risk citation |
| `ResearchReport` | Research citation |
| `QuantitativeRiskReport` | Quant citation |

Future report types **SHALL remain additive**. Changing required → optional
(or the reverse) requires freeze amendment.

Report policy validation: **PASS**

---

## 7. Architectural principles (frozen)

| Principle | Meaning |
|---|---|
| Single ownership | Upstream aggregates stay with frozen domains |
| Reference-only integration | Digests / ids / status / version only |
| Immutable graph | Frozen artifacts; new builds emit new reports |
| Explainability-first | Lineage + EvidenceLink are first-class |
| No ownership leakage | Never absorb business facts |
| Stable public contracts | Public `__init__` façade; additive re-exports |

---

## 8. Extension model (frozen)

Future work remains **additive**:

| Extension | Pattern |
|---|---|
| Graph database adapters | Adapter projecting `KnowledgeGraphReport` outward |
| Visualization | UI / app layer over report |
| Semantic search | Adapter / index outside domain |
| Embeddings | Copilot / adapter — not domain core |
| Knowledge inference | Additive methods / limitation notes — no silent business conclusions |
| Cross-workspace graphs | Additive identity / corpus namespaces |
| Incremental graph updates | Additive builder / checkpoint fields |

**No redesign** of ownership, cite-only rule, required report anchors, or
Models → Assembler → Engine → Reporter pipeline.

---

## 9. Implementation roadmap (post-freeze)

| Phase | Scope | Status |
|---|---|---|
| **I0.0** | Design | **DONE** |
| **I0.0A** | Architecture freeze (this document) | **DONE / FROZEN** |
| **I1.0** | Domain models in `packages/knowledge_graph/` | **DONE** · see [I1.0](I1_0_KNOWLEDGE_GRAPH_DOMAIN_MODELS.md) |
| **I1.1** | KnowledgeGraphAssembler | **DONE** · see [I1.1](I1_1_KNOWLEDGE_GRAPH_ASSEMBLER.md) |
| **I1.2** | KnowledgeGraphEngine | **DONE** · see [I1.2](I1_2_KNOWLEDGE_GRAPH_ENGINE.md) |
| **I1.3** | KnowledgeGraphReporter | **DONE** · see [I1.3](I1_3_KNOWLEDGE_GRAPH_REPORTER.md) |
| **I1.4** | Validation & freeze | **DONE / FROZEN** · see [I1.4](I1_4_KNOWLEDGE_GRAPH_VALIDATION_AND_FREEZE.md) |

**I1.0 acceptance gate:**

1. This freeze remains in force.  
2. Work lives in `packages/knowledge_graph/` with dependencies ⊆ `{core}`.  
3. Existing **1385+** tests stay green; changes are additive.  
4. No vendor graph-DB / persistence / LLM SDKs in domain; no business analysis.  
5. Recommendation / Workflow / Quant / Research / Risk freezes remain untouched.  
6. Required report anchors (`RecommendationReport`, `WorkflowReport`) are cited
   via local refs — never embedded.

---

## 10. Known technical debt (document only)

1. **Ontology evolution** — richer industry / instrument ontologies additive.  
2. **Large graph partitioning** — corpus sharding / windows deferred.  
3. **Incremental builders** — full rebuild first; incremental updates additive.  
4. **Storage adapters** — persistence / graph-DB projection outside domain.  
5. **Visualization layer** — UI / Copilot adapters outside domain.  
6. **Exact report façade type aliases** — naming of Analysis/Decision/Portfolio
   report types vs package-local refs resolved at I1.0 models.  
7. **Multi-corpus identity** — investigation vs platform-wide graphs as
   additive identity namespaces.

---

## 11. Freeze confirmation

**CONFIRMED.**

Knowledge Graph architecture (independence, ownership, dependency direction,
Assembler → Engine → Reporter pipeline, taxonomy, report policy, extension
model) is fully frozen and ready for **I1.0** implementation.

---

## 12. PASS / FAIL

**PASS** — Knowledge Graph architecture is frozen.

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | **Authoritative Knowledge Graph architecture freeze** |
| [I0_0_KNOWLEDGE_GRAPH_DESIGN.md](I0_0_KNOWLEDGE_GRAPH_DESIGN.md) | Design (historical on conflicts) |
| [H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md](H1_4_WORKFLOW_VALIDATION_AND_FREEZE.md) | Workflow freeze |
| [G1_4_RECOMMENDATION_VALIDATION_AND_FREEZE.md](G1_4_RECOMMENDATION_VALIDATION_AND_FREEZE.md) | Recommendation freeze |
| [DSP_ARCHITECTURE_BASELINE_v1_0.md](DSP_ARCHITECTURE_BASELINE_v1_0.md) | Platform baseline |

---

## Final question

Is the Knowledge Graph architecture fully validated, architecturally frozen,
and ready for implementation (I1.0)?

**YES**
