# Phase I1.2 — Knowledge Graph Engine

**Status:** Implemented · Deterministic cite-only topology · No business analysis  

**Package:** `packages/knowledge_graph/` **0.3.0**  
**Freeze:** [I0.0A](I0_0A_KNOWLEDGE_GRAPH_ARCHITECTURE_FREEZE.md)  
**Assembler:** [I1.1](I1_1_KNOWLEDGE_GRAPH_ASSEMBLER.md)

## Engine architecture

```text
AssemblyResult / GraphProfile
  (validated Recommendation + Workflow anchors + optional refs)
        │
        ▼
KnowledgeGraphEngine.synthesize
        │
        ├── GraphNode[]          (one per citation)
        ├── GraphRelationship[]  (used taxonomy categories)
        ├── GraphEdge[]          (EXECUTED_BY / DERIVES_FROM /
        │                         SUPPORTED_BY / REFERENCES)
        ├── EvidenceLink[]       (DIRECT)
        ├── Lineage[]            (REPORT / EXECUTION / EVIDENCE)
        ├── GraphSummary
        └── KnowledgeGraphReport (populated)
```

APIs: `KnowledgeGraphEngine`, `EngineContext`, `EngineResult`, `EngineStatus`.  
Method id: `dsp.knowledge_graph.method.topology.v1`

## Graph construction algorithm

1. Collect refs in stable kind order; sort within kind by `(id, report_id)`.  
2. Emit one `GraphNode` per ref (`dsp.kg.node.{kind}.{ref.id}`) with frozen
   category mapping (never invent companies/securities).  
3. Emit edges:
   - Recommendation → Workflow: `EXECUTED_BY`  
   - Recommendation → optional upstream: `DERIVES_FROM`  
   - Recommendation/Research → Evidence: `SUPPORTED_BY`  
   - Workflow → Recommendation: `REFERENCES`  
4. Emit `GraphRelationship` descriptors for used categories only.  
5. Emit `EvidenceLink` (`DIRECT`) for recommendation/research → evidence.  
6. Emit lineage chains and summary counts.  
7. Validate uniqueness, orphans, and taxonomy legality.

## Relationship generation policy

Only frozen `RelationshipCategory` values. No financial conclusions. Edges are
structural citations among report/evidence/workflow/recommendation nodes.

## Evidence-link generation

`DIRECT` links from recommendation and research nodes to industry-evidence
nodes when those citations exist. Empty when no evidence refs.

## Lineage generation

| Category | Contents (sorted) |
|---|---|
| `REPORT` | REPORT / RECOMMENDATION / RISK / RESEARCH / PORTFOLIO nodes |
| `EXECUTION` | WORKFLOW then RECOMMENDATION nodes |
| `EVIDENCE` | EVIDENCE nodes (omitted if none) |

## Validation rules

Duplicate node/edge/relationship/evidence/lineage ids · broken / orphan edges ·
orphan nodes · engine/report identity mismatch · `synthesize_many` uniqueness.

## Determinism guarantees

Same assembly citations → identical node ids, edge order, lineage order, and
report collections. No randomness, clocks, or external I/O.

## Future extension strategy

| Phase | Scope |
|---|---|
| **I1.3** | Reporter — presentation / navigation | **DONE** ([I1.3](I1_3_KNOWLEDGE_GRAPH_REPORTER.md)) |
| **I1.4** | Validation & freeze | **DONE / FROZEN** ([I1.4](I1_4_KNOWLEDGE_GRAPH_VALIDATION_AND_FREEZE.md)) |

Additive taxonomies / methods only. Graph DB / search / embeddings remain
external adapters.

## Non-goals (this phase)

Traversal, querying, persistence, graph databases, semantic search, embeddings,
ontology inference, LLM reasoning, business analysis.
