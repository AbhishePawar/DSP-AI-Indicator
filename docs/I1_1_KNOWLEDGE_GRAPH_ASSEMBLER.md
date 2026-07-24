# Phase I1.1 — Knowledge Graph Assembler

**Status:** Implemented · Construction / citations only · No inference  

**Package:** `packages/knowledge_graph/` **0.2.0**  
**Freeze:** [I0.0A](I0_0A_KNOWLEDGE_GRAPH_ARCHITECTURE_FREEZE.md)  
**Models:** [I1.0](I1_0_KNOWLEDGE_GRAPH_DOMAIN_MODELS.md)

## Assembler architecture

```text
AssemblyContext
  ├── GraphIdentity
  ├── GraphMetadata
  ├── RecommendationReference[]  (required)
  ├── WorkflowReference[]        (required)
  └── optional upstream OutcomeReference[]
        │
        ▼
KnowledgeGraphAssembler.assemble
        │
        ├── GraphProfile  (empty nodes / edges / relationships /
        │                  evidence links / lineage)
        ├── KnowledgeGraphReport (skeleton + validated refs)
        ├── GraphSummary  (counts = 0 + assembly limitations)
        └── AssemblyResult (status + warnings)
```

| Does | Does not |
|---|---|
| Validate required anchors | Infer nodes or edges |
| Normalize / preserve citations | Traverse or query |
| Detect missing / duplicate refs | Calculate lineage |
| Build deterministic empty skeleton | Persist or open graph DBs |

## Construction policy

1. Require `GraphIdentity`, `GraphMetadata`, ≥1 Recommendation ref, ≥1 Workflow
   ref.  
2. Emit empty `nodes`, `edges`, `relationships`, `evidence_links`, `lineages`.  
3. Summary counts are zero with assembly limitation notes.  
4. Optional upstream refs pass through when present.

## Anchor policy

I0.0A required anchors: **RecommendationReport** and **WorkflowReport** citations.
Missing either raises `KnowledgeGraphError`.

## Validation rules

Missing Recommendation / Workflow anchors · duplicate report references ·
broken digests / report ids · duplicate graph identities in `assemble_many`.

## Reference normalization

Refs pass through frozen constructors. Assembler never embeds upstream payloads.

## Empty graph policy

Assembler intentionally leaves graph collections empty. Engine (I1.2) owns
deterministic structure assembly from citations — not this phase.

## Future extension strategy

| Phase | Scope |
|---|---|
| **I1.2** | KnowledgeGraphEngine — relationship / lineage assembly | **DONE** ([I1.2](I1_2_KNOWLEDGE_GRAPH_ENGINE.md)) |
| **I1.3** | Reporter | **DONE** ([I1.3](I1_3_KNOWLEDGE_GRAPH_REPORTER.md)) |
| **I1.4** | Validation & freeze | **DONE / FROZEN** ([I1.4](I1_4_KNOWLEDGE_GRAPH_VALIDATION_AND_FREEZE.md)) |

## Non-goals (this phase)

Graph building, relationship inference, traversal, querying, persistence,
graph databases, LLM reasoning.
