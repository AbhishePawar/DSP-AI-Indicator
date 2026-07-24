# Phase I1.3 — Knowledge Graph Reporter

**Status:** Implemented · Presentation only · No topology construction  

**Package:** `packages/knowledge_graph/` **0.4.0**  
**Freeze:** [I0.0A](I0_0A_KNOWLEDGE_GRAPH_ARCHITECTURE_FREEZE.md)  
**Engine:** [I1.2](I1_2_KNOWLEDGE_GRAPH_ENGINE.md)

## Reporter architecture

```text
KnowledgeGraphReport  ──┐
EngineResult          ──┼──► ReportingContext
GraphProfile (opt.)   ──┘
                  │
                  ▼
          KnowledgeGraphReporter
                  │
                  ├── ReportMetadata + summary sections
                  ├── CollectionStatistics (nodes / edges /
                  │     relationships / evidence links / lineage)
                  ├── ValidationStatusView
                  ├── GraphSummary / GraphMetadata (pass-through)
                  ├── referenced report ids
                  ├── KnowledgeGraphReport (limitations append only)
                  └── ReportingResult
```

APIs: `KnowledgeGraphReporter`, `ReportingContext`, `ReportingResult`,
`ReportingStatus`, `ReportMetadata`, `CollectionStatistics`,
`CategoryCount`, `ValidationStatusView`.

## Presentation policy

| Present | Behavior |
|---|---|
| Graph summary | Pass-through `GraphSummary` |
| Node statistics | Counts by `NodeCategory` |
| Edge statistics | Counts by `RelationshipCategory` |
| Relationship statistics | Counts by relationship category |
| Evidence-link statistics | Counts by `EvidenceLinkCategory` |
| Lineage statistics | Counts by `LineageCategory` |
| Metadata | Pass-through `GraphMetadata` + presentation `ReportMetadata` |
| Validation status | Structural presentation flags (identity / method / provenance / anchors) |
| Limitations | Merge report + summary + context notes; append presentation-only note |

## Validation rules

Missing graph identity · engine/report identity mismatch · reporter/report
(profile) mismatch · duplicate report sections · broken references · missing
provenance · missing method_id (when topology present) · missing metadata ·
immutable outputs · `report_many` uniqueness.

## Metadata policy

- Preserve `GraphMetadata` object identity from the source report.  
- `ReportMetadata` is presentation-only (counts, section keys, method id).  
- Never invent corpus ownership or tags.

## Limitations

Reporter may append a presentation-only limitation via `dataclasses.replace`.
It never mutates the source report object, never rebuilds nodes/edges, and
never rewrites lineage.

## Future extension strategy

| Phase | Scope |
|---|---|
| **I1.4** | Validation & architecture freeze | **DONE / FROZEN** ([I1.4](I1_4_KNOWLEDGE_GRAPH_VALIDATION_AND_FREEZE.md)) |

Additive section keys / UI adapters outside this package. No redesign of
Models → Assembler → Engine → Reporter (I0.0A).

## Non-goals (this phase)

Graph construction, relationship generation, lineage generation, traversal,
querying, persistence, graph databases, embeddings, semantic search,
ontology inference, LLM reasoning, business analysis.

## Related documents

| Doc | Role |
|---|---|
| [I1.2](I1_2_KNOWLEDGE_GRAPH_ENGINE.md) | Engine |
| [I1.1](I1_1_KNOWLEDGE_GRAPH_ASSEMBLER.md) | Assembler |
| [I1.0](I1_0_KNOWLEDGE_GRAPH_DOMAIN_MODELS.md) | Models |
| [I0.0A](I0_0A_KNOWLEDGE_GRAPH_ARCHITECTURE_FREEZE.md) | Freeze |
