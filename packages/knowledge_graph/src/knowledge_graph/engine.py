"""Knowledge Graph Engine — deterministic topology from citations (I1.2).

Builds nodes, edges, relationships, evidence links, and lineage strictly from
validated immutable report references. Never performs business analysis,
modifies upstream reports, traverses, queries, or persists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from knowledge_graph.assembler import AssemblyResult
from knowledge_graph.enums import (
    EngineStatus,
    EvidenceLinkCategory,
    LineageCategory,
    NodeCategory,
    RelationshipCategory,
)
from knowledge_graph.exceptions import KnowledgeGraphError
from knowledge_graph.models import (
    EvidenceLink,
    GraphEdge,
    GraphNode,
    GraphProfile,
    GraphRelationship,
    GraphSummary,
    KnowledgeGraphReport,
    Lineage,
)
from knowledge_graph.validation import assert_unique_graph_ids

__all__ = [
    "EngineContext",
    "EngineResult",
    "KnowledgeGraphEngine",
]

METHOD_TOPOLOGY = "dsp.knowledge_graph.method.topology.v1"
_ENGINE_PROVENANCE = ("knowledge_graph.engine", METHOD_TOPOLOGY)

# Stable kind → node category mapping (frozen taxonomy only).
_KIND_CATEGORY: dict[str, NodeCategory] = {
    "analysis": NodeCategory.REPORT,
    "decision": NodeCategory.REPORT,
    "industry_evidence": NodeCategory.EVIDENCE,
    "comparison": NodeCategory.REPORT,
    "portfolio": NodeCategory.PORTFOLIO,
    "risk": NodeCategory.RISK,
    "research": NodeCategory.RESEARCH,
    "quantitative_risk": NodeCategory.RISK,
    "recommendation": NodeCategory.RECOMMENDATION,
    "workflow": NodeCategory.WORKFLOW,
}

_DERIVE_KINDS = frozenset(
    {
        "analysis",
        "decision",
        "industry_evidence",
        "comparison",
        "portfolio",
        "risk",
        "research",
        "quantitative_risk",
    }
)


@dataclass(frozen=True, slots=True)
class EngineContext:
    """Inputs for deterministic Knowledge Graph topology assembly."""

    assembly: AssemblyResult
    profile: GraphProfile | None = None

    def __post_init__(self) -> None:
        if self.assembly is None:
            msg = "AssemblyResult is required"
            raise KnowledgeGraphError(msg)


@dataclass(frozen=True, slots=True)
class EngineResult:
    """Immutable engine output — populated graph profile / report."""

    graph_id: str
    status: EngineStatus
    profile: GraphProfile
    report: KnowledgeGraphReport
    summary: GraphSummary
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    relationships: tuple[GraphRelationship, ...]
    evidence_links: tuple[EvidenceLink, ...]
    lineages: tuple[Lineage, ...]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))
        object.__setattr__(self, "relationships", tuple(self.relationships))
        object.__setattr__(self, "evidence_links", tuple(self.evidence_links))
        object.__setattr__(self, "lineages", tuple(self.lineages))
        object.__setattr__(self, "warnings", tuple(self.warnings))


class KnowledgeGraphEngine:
    """Canonical deterministic graph topology builder from report citations."""

    def validate_inputs(self, context: EngineContext) -> None:
        """Reject invalid topology inputs."""
        if context is None or context.assembly is None:
            msg = "EngineContext.assembly is required"
            raise KnowledgeGraphError(msg)
        profile = context.profile or context.assembly.profile
        report = context.assembly.report
        if profile is None:
            msg = "missing GraphProfile"
            raise KnowledgeGraphError(msg)
        if report is None:
            msg = "missing KnowledgeGraphReport"
            raise KnowledgeGraphError(msg)
        if profile.graph_id != report.graph_id:
            msg = (
                "engine/report identity mismatch: "
                f"profile {profile.graph_id!r} vs report {report.graph_id!r}"
            )
            raise KnowledgeGraphError(msg)
        if (
            context.profile is not None
            and context.profile.graph_id != context.assembly.profile.graph_id
        ):
            msg = (
                "engine/report identity mismatch: context profile "
                f"{context.profile.graph_id!r} vs assembly "
                f"{context.assembly.profile.graph_id!r}"
            )
            raise KnowledgeGraphError(msg)
        if not profile.recommendation_refs:
            msg = "broken references: RecommendationReference required"
            raise KnowledgeGraphError(msg)
        if not profile.workflow_refs:
            msg = "broken references: WorkflowReference required"
            raise KnowledgeGraphError(msg)

    def synthesize(
        self, context: EngineContext | AssemblyResult
    ) -> EngineResult:
        """Build deterministic topology and emit a populated KnowledgeGraphReport."""
        ctx = (
            EngineContext(assembly=context)
            if isinstance(context, AssemblyResult)
            else context
        )
        self.validate_inputs(ctx)
        profile = ctx.profile or ctx.assembly.profile
        base_report = ctx.assembly.report
        warnings: list[str] = []

        ref_entries = self._collect_ref_entries(profile)
        if not any(kind in _DERIVE_KINDS for kind, _ in ref_entries):
            warnings.append(
                "optional upstream refs absent; topology uses anchors only."
            )

        nodes = self._build_nodes(ref_entries)
        node_by_id = {n.node_id: n for n in nodes}
        recommendation_ids = tuple(
            n.node_id
            for n in nodes
            if n.category is NodeCategory.RECOMMENDATION
        )
        workflow_ids = tuple(
            n.node_id for n in nodes if n.category is NodeCategory.WORKFLOW
        )
        evidence_ids = tuple(
            n.node_id for n in nodes if n.category is NodeCategory.EVIDENCE
        )
        research_ids = tuple(
            n.node_id for n in nodes if n.category is NodeCategory.RESEARCH
        )
        derive_ids = tuple(
            self._node_id(kind, ref.id)
            for kind, ref in ref_entries
            if kind in _DERIVE_KINDS
        )

        edges = self._build_edges(
            recommendation_ids=recommendation_ids,
            workflow_ids=workflow_ids,
            derive_ids=derive_ids,
            evidence_ids=evidence_ids,
            research_ids=research_ids,
        )
        used_categories = frozenset(e.relationship_category for e in edges)
        relationships = self._build_relationships(used_categories)
        evidence_links = self._build_evidence_links(
            recommendation_ids=recommendation_ids,
            research_ids=research_ids,
            evidence_ids=evidence_ids,
        )
        lineages = self._build_lineages(nodes)

        self._validate_graph(
            nodes=nodes,
            edges=edges,
            relationships=relationships,
            evidence_links=evidence_links,
            lineages=lineages,
            node_by_id=node_by_id,
        )

        summary = GraphSummary(
            node_count=len(nodes),
            edge_count=len(edges),
            relationship_count=len(relationships),
            evidence_link_count=len(evidence_links),
            lineage_count=len(lineages),
            limitation_notes=(
                f"Topology method {METHOD_TOPOLOGY} — cite-only construction; "
                "no business analysis or upstream report mutation.",
                *(profile.summary.limitation_notes if profile.summary else ()),
            ),
        )

        new_profile = GraphProfile(
            identity=profile.identity,
            metadata=profile.metadata,
            nodes=nodes,
            edges=edges,
            relationships=relationships,
            evidence_links=evidence_links,
            lineages=lineages,
            summary=summary,
            analysis_refs=profile.analysis_refs,
            decision_refs=profile.decision_refs,
            industry_evidence_refs=profile.industry_evidence_refs,
            comparison_refs=profile.comparison_refs,
            portfolio_refs=profile.portfolio_refs,
            risk_refs=profile.risk_refs,
            research_refs=profile.research_refs,
            quantitative_risk_refs=profile.quantitative_risk_refs,
            recommendation_refs=profile.recommendation_refs,
            workflow_refs=profile.workflow_refs,
            notes=profile.notes,
        )
        new_report = KnowledgeGraphReport(
            graph_id=profile.graph_id,
            summary=summary,
            metadata=profile.metadata,
            as_of=base_report.as_of,
            nodes=nodes,
            edges=edges,
            relationships=relationships,
            evidence_links=evidence_links,
            lineages=lineages,
            analysis_refs=profile.analysis_refs,
            decision_refs=profile.decision_refs,
            industry_evidence_refs=profile.industry_evidence_refs,
            comparison_refs=profile.comparison_refs,
            portfolio_refs=profile.portfolio_refs,
            risk_refs=profile.risk_refs,
            research_refs=profile.research_refs,
            quantitative_risk_refs=profile.quantitative_risk_refs,
            recommendation_refs=profile.recommendation_refs,
            workflow_refs=profile.workflow_refs,
            limitations=(
                "KnowledgeGraphReport populated by Knowledge Graph Engine — "
                "Reporter (I1.3) may refine presentation.",
                *summary.limitation_notes,
                *base_report.limitations,
            ),
        )

        status = (
            EngineStatus.PARTIAL if warnings else EngineStatus.COMPLETE
        )
        return EngineResult(
            graph_id=profile.graph_id,
            status=status,
            profile=new_profile,
            report=new_report,
            summary=summary,
            nodes=nodes,
            edges=edges,
            relationships=relationships,
            evidence_links=evidence_links,
            lineages=lineages,
            warnings=tuple(warnings),
        )

    def synthesize_many(
        self, contexts: tuple[EngineContext, ...]
    ) -> tuple[EngineResult, ...]:
        """Synthesize many contexts; reject duplicate graph identities."""
        assert_unique_graph_ids(
            tuple(
                (c.profile or c.assembly.profile).graph_id for c in contexts
            )
        )
        return tuple(self.synthesize(context) for context in contexts)

    def _collect_ref_entries(
        self, profile: GraphProfile
    ) -> tuple[tuple[str, Any], ...]:
        groups: tuple[tuple[str, tuple[Any, ...]], ...] = (
            ("analysis", profile.analysis_refs),
            ("decision", profile.decision_refs),
            ("industry_evidence", profile.industry_evidence_refs),
            ("comparison", profile.comparison_refs),
            ("portfolio", profile.portfolio_refs),
            ("risk", profile.risk_refs),
            ("research", profile.research_refs),
            ("quantitative_risk", profile.quantitative_risk_refs),
            ("recommendation", profile.recommendation_refs),
            ("workflow", profile.workflow_refs),
        )
        entries: list[tuple[str, Any]] = []
        for kind, refs in groups:
            for ref in sorted(refs, key=lambda r: (r.id, r.report_id)):
                entries.append((kind, ref))
        return tuple(entries)

    def _node_id(self, kind: str, ref_id: str) -> str:
        return f"dsp.kg.node.{kind}.{ref_id}"

    def _build_nodes(
        self, entries: tuple[tuple[str, Any], ...]
    ) -> tuple[GraphNode, ...]:
        nodes: list[GraphNode] = []
        seen: set[str] = set()
        for kind, ref in entries:
            node_id = self._node_id(kind, ref.id)
            if node_id in seen:
                msg = f"duplicate node ids: {node_id!r}"
                raise KnowledgeGraphError(msg)
            seen.add(node_id)
            category = _KIND_CATEGORY[kind]
            nodes.append(
                GraphNode(
                    node_id=node_id,
                    category=category,
                    label=f"{kind}:{ref.report_id}",
                    provenance=_ENGINE_PROVENANCE,
                    external_ref_id=ref.id,
                    notes=(f"cite {ref.digest}",),
                )
            )
        return tuple(nodes)

    def _build_relationships(
        self, used: frozenset[RelationshipCategory]
    ) -> tuple[GraphRelationship, ...]:
        relationships: list[GraphRelationship] = []
        for category in sorted(used, key=lambda c: c.value):
            relationships.append(
                GraphRelationship(
                    relationship_id=f"dsp.kg.rel.{category.value}",
                    category=category,
                    title=category.value.replace("_", " "),
                    provenance=_ENGINE_PROVENANCE,
                )
            )
        return tuple(relationships)

    def _build_edges(
        self,
        *,
        recommendation_ids: tuple[str, ...],
        workflow_ids: tuple[str, ...],
        derive_ids: tuple[str, ...],
        evidence_ids: tuple[str, ...],
        research_ids: tuple[str, ...],
    ) -> tuple[GraphEdge, ...]:
        edges: list[GraphEdge] = []
        edge_n = 0

        def _add(
            *,
            source: str,
            target: str,
            category: RelationshipCategory,
            relationship_id: str,
        ) -> None:
            nonlocal edge_n
            edge_n += 1
            edges.append(
                GraphEdge(
                    edge_id=f"dsp.kg.edge.{edge_n:04d}",
                    source_node_id=source,
                    target_node_id=target,
                    relationship_category=category,
                    relationship_id=relationship_id,
                    provenance=_ENGINE_PROVENANCE,
                )
            )

        # Recommendation EXECUTED_BY Workflow (stable nested loops).
        for rec in sorted(recommendation_ids):
            for wf in sorted(workflow_ids):
                _add(
                    source=rec,
                    target=wf,
                    category=RelationshipCategory.EXECUTED_BY,
                    relationship_id="dsp.kg.rel.executed_by",
                )

        # Recommendation DERIVES_FROM optional upstream citations.
        for rec in sorted(recommendation_ids):
            for upstream in sorted(derive_ids):
                _add(
                    source=rec,
                    target=upstream,
                    category=RelationshipCategory.DERIVES_FROM,
                    relationship_id="dsp.kg.rel.derives_from",
                )

        # Research / Recommendation SUPPORTED_BY Evidence.
        for source in sorted((*recommendation_ids, *research_ids)):
            for evidence in sorted(evidence_ids):
                _add(
                    source=source,
                    target=evidence,
                    category=RelationshipCategory.SUPPORTED_BY,
                    relationship_id="dsp.kg.rel.supported_by",
                )

        # Workflow REFERENCES Recommendation (execution cites outcome).
        for wf in sorted(workflow_ids):
            for rec in sorted(recommendation_ids):
                _add(
                    source=wf,
                    target=rec,
                    category=RelationshipCategory.REFERENCES,
                    relationship_id="dsp.kg.rel.references",
                )

        return tuple(edges)

    def _build_evidence_links(
        self,
        *,
        recommendation_ids: tuple[str, ...],
        research_ids: tuple[str, ...],
        evidence_ids: tuple[str, ...],
    ) -> tuple[EvidenceLink, ...]:
        links: list[EvidenceLink] = []
        n = 0
        for source in sorted((*recommendation_ids, *research_ids)):
            for evidence in sorted(evidence_ids):
                n += 1
                links.append(
                    EvidenceLink(
                        link_id=f"dsp.kg.evidence.{n:04d}",
                        category=EvidenceLinkCategory.DIRECT,
                        source_node_id=source,
                        target_node_id=evidence,
                        provenance=_ENGINE_PROVENANCE,
                    )
                )
        return tuple(links)

    def _build_lineages(
        self, nodes: tuple[GraphNode, ...]
    ) -> tuple[Lineage, ...]:
        by_cat: dict[NodeCategory, list[str]] = {}
        for node in nodes:
            by_cat.setdefault(node.category, []).append(node.node_id)
        for ids in by_cat.values():
            ids.sort()

        report_ids = tuple(
            nid
            for cat in (
                NodeCategory.REPORT,
                NodeCategory.RECOMMENDATION,
                NodeCategory.RISK,
                NodeCategory.RESEARCH,
                NodeCategory.PORTFOLIO,
            )
            for nid in by_cat.get(cat, ())
        )
        execution_ids = tuple(
            [
                *by_cat.get(NodeCategory.WORKFLOW, ()),
                *by_cat.get(NodeCategory.RECOMMENDATION, ()),
            ]
        )
        evidence_ids = tuple(by_cat.get(NodeCategory.EVIDENCE, ()))

        lineages: list[Lineage] = []
        if report_ids:
            lineages.append(
                Lineage(
                    lineage_id="dsp.kg.lineage.report",
                    category=LineageCategory.REPORT,
                    node_ids=report_ids,
                    provenance=_ENGINE_PROVENANCE,
                )
            )
        if execution_ids:
            lineages.append(
                Lineage(
                    lineage_id="dsp.kg.lineage.execution",
                    category=LineageCategory.EXECUTION,
                    node_ids=execution_ids,
                    provenance=_ENGINE_PROVENANCE,
                )
            )
        if evidence_ids:
            lineages.append(
                Lineage(
                    lineage_id="dsp.kg.lineage.evidence",
                    category=LineageCategory.EVIDENCE,
                    node_ids=evidence_ids,
                    provenance=_ENGINE_PROVENANCE,
                )
            )
        return tuple(lineages)

    def _validate_graph(
        self,
        *,
        nodes: tuple[GraphNode, ...],
        edges: tuple[GraphEdge, ...],
        relationships: tuple[GraphRelationship, ...],
        evidence_links: tuple[EvidenceLink, ...],
        lineages: tuple[Lineage, ...],
        node_by_id: dict[str, GraphNode],
    ) -> None:
        node_ids = set(node_by_id)
        edge_ids: set[str] = set()
        for edge in edges:
            if edge.edge_id in edge_ids:
                msg = f"duplicate edge ids: {edge.edge_id!r}"
                raise KnowledgeGraphError(msg)
            edge_ids.add(edge.edge_id)
            if edge.source_node_id not in node_ids:
                msg = f"orphan edges: source {edge.source_node_id!r} missing"
                raise KnowledgeGraphError(msg)
            if edge.target_node_id not in node_ids:
                msg = f"orphan edges: target {edge.target_node_id!r} missing"
                raise KnowledgeGraphError(msg)

        rel_ids: set[str] = set()
        for rel in relationships:
            if rel.relationship_id in rel_ids:
                msg = f"duplicate relationships: {rel.relationship_id!r}"
                raise KnowledgeGraphError(msg)
            rel_ids.add(rel.relationship_id)

        link_ids: set[str] = set()
        for link in evidence_links:
            if link.link_id in link_ids:
                msg = f"duplicate evidence links: {link.link_id!r}"
                raise KnowledgeGraphError(msg)
            link_ids.add(link.link_id)

        lineage_ids: set[str] = set()
        for lineage in lineages:
            if lineage.lineage_id in lineage_ids:
                msg = f"duplicate lineage ids: {lineage.lineage_id!r}"
                raise KnowledgeGraphError(msg)
            lineage_ids.add(lineage.lineage_id)

        connected: set[str] = set()
        for edge in edges:
            connected.add(edge.source_node_id)
            connected.add(edge.target_node_id)
        for link in evidence_links:
            connected.add(link.source_node_id)
            connected.add(link.target_node_id)
        orphans = sorted(node_ids - connected)
        if orphans:
            msg = f"orphan nodes: {orphans}"
            raise KnowledgeGraphError(msg)
