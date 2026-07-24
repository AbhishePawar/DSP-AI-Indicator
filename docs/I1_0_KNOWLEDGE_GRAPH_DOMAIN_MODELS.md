# Phase I1.0 — Knowledge Graph Domain Models

**Status:** Implemented · Structure only · No assembler / engine / reporter  

**Package:** `packages/knowledge_graph/` **0.1.0**  
**Freeze:** [I0.0A](I0_0A_KNOWLEDGE_GRAPH_ARCHITECTURE_FREEZE.md)

## Ownership

Knowledge Graph owns **only**:

| Model | Role |
|---|---|
| `GraphIdentity` | Graph / corpus identity |
| `GraphProfile` | Aggregate root |
| `GraphNode` | Typed vertex |
| `GraphEdge` | Directed typed connection |
| `GraphRelationship` | Named relationship descriptor |
| `EvidenceLink` | Cite-backed evidence association |
| `Lineage` | Ordered provenance chain |
| `GraphSummary` | Counts / limitations |
| `KnowledgeGraphReport` | Canonical immutable presentation snapshot |
| `GraphMetadata` | Corpus / as-of / tags |

Upstream Decision / Evidence / Comparison / Portfolio / Risk / Research / Quant /
Recommendation / Workflow remain **reference-only**.

## Model hierarchy

```
GraphIdentity
GraphMetadata
GraphNode / GraphRelationship / GraphEdge
EvidenceLink / Lineage
        │
        ▼
GraphProfile (aggregate)
        │
        ▼
GraphSummary
        │
        ▼
KnowledgeGraphReport
```

## Reference policy

References contain only: `id`, `report_id`, `version`, `digest`, `status`,
`generated_at`. Never embed upstream reports.

**Required anchors (I0.0A):** `RecommendationReference`, `WorkflowReference`  
**Optional:** Analysis, Decision, Industry Evidence, Comparison, Portfolio,
Risk, Research, Quantitative Risk.

## Validation rules

Duplicate node / edge / relationship ids; broken node/edge/evidence/lineage
links; illegal taxonomy categories; missing provenance; duplicate report
references; missing required anchors; Decimal-only edge weights; frozen
dataclasses.

## Immutability

All domain models are frozen dataclasses (`frozen=True`, `slots=True`).

## Taxonomy

See [I0.0A](I0_0A_KNOWLEDGE_GRAPH_ARCHITECTURE_FREEZE.md) §5 — `NodeCategory`,
`RelationshipCategory`, `EvidenceLinkCategory`, `LineageCategory`.

## Public API

Stable façade: `knowledge_graph` package `__init__.py`. Version: **`0.1.0`**.

## Future extension strategy

- **I1.1** Assembler — **DONE** ([I1.1](I1_1_KNOWLEDGE_GRAPH_ASSEMBLER.md))
- **I1.2** Engine — relationship / lineage assembly · **DONE** ([I1.2](I1_2_KNOWLEDGE_GRAPH_ENGINE.md))  
- **I1.3** Reporter · **DONE** ([I1.3](I1_3_KNOWLEDGE_GRAPH_REPORTER.md))
- **I1.4** Validation & freeze · **DONE / FROZEN** ([I1.4](I1_4_KNOWLEDGE_GRAPH_VALIDATION_AND_FREEZE.md))
- Graph DB / viz / search remain external adapters  

## Non-goals (this phase)

Graph construction, traversal, querying, persistence, business analysis.
