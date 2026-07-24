"""Knowledge Graph domain models — contracts only (I1.0).

Immutable value objects and aggregate. No graph construction, traversal,
querying, or persistence.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from core.exceptions import ValidationError

from knowledge_graph.enums import (
    EvidenceLinkCategory,
    LineageCategory,
    NodeCategory,
    RelationshipCategory,
)
from knowledge_graph.exceptions import KnowledgeGraphError
from knowledge_graph.refs import (
    AnalysisReference,
    ComparisonReference,
    DecisionReference,
    IndustryEvidenceReference,
    PortfolioReference,
    QuantitativeRiskReference,
    RecommendationReference,
    ResearchReference,
    RiskReference,
    WorkflowReference,
    _normalize_id,
)
from knowledge_graph.validation import (
    assert_evidence_link_category,
    assert_lineage_category,
    assert_node_category,
    assert_relationship_category,
    require_decimal,
)

__all__ = [
    "EvidenceLink",
    "GraphEdge",
    "GraphIdentity",
    "GraphMetadata",
    "GraphNode",
    "GraphProfile",
    "GraphRelationship",
    "GraphSummary",
    "KnowledgeGraphReport",
    "Lineage",
]


def _non_empty(text: str, *, field: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        msg = f"{field} must not be empty"
        raise ValidationError(msg)
    return cleaned


@dataclass(frozen=True, slots=True)
class GraphIdentity:
    """Canonical identity of a Knowledge Graph profile / corpus."""

    graph_id: str
    graph_name: str
    created_at: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        graph_id = _normalize_id(self.graph_id, field="graph_id")
        name = _non_empty(self.graph_name, field="graph_name")
        created_at = (
            None if self.created_at is None else self.created_at.strip() or None
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "graph_id", graph_id)
        object.__setattr__(self, "graph_name", name)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class GraphMetadata:
    """Descriptive graph metadata — not a business score."""

    corpus_id: str
    as_of: str
    owner: str | None = None
    tags: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        corpus_id = _normalize_id(self.corpus_id, field="corpus_id")
        as_of = _non_empty(self.as_of, field="as_of")
        owner = None if self.owner is None else self.owner.strip() or None
        tags = tuple(t.strip() for t in self.tags if t.strip())
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "corpus_id", corpus_id)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "owner", owner)
        object.__setattr__(self, "tags", tags)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class GraphNode:
    """Typed graph vertex — never embeds upstream report payloads."""

    node_id: str
    category: NodeCategory
    label: str
    provenance: tuple[str, ...]
    external_ref_id: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        node_id = _normalize_id(self.node_id, field="node_id")
        assert_node_category(self.category)
        label = _non_empty(self.label, field="label")
        if not self.provenance:
            msg = "missing provenance: GraphNode requires provenance"
            raise KnowledgeGraphError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        external = (
            None
            if self.external_ref_id is None
            else _normalize_id(self.external_ref_id, field="external_ref_id")
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "node_id", node_id)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "external_ref_id", external)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class GraphRelationship:
    """Named relationship descriptor — taxonomy-bound."""

    relationship_id: str
    category: RelationshipCategory
    title: str
    provenance: tuple[str, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        relationship_id = _normalize_id(
            self.relationship_id, field="relationship_id"
        )
        assert_relationship_category(self.category)
        title = _non_empty(self.title, field="title")
        if not self.provenance:
            msg = "missing provenance: GraphRelationship requires provenance"
            raise KnowledgeGraphError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "relationship_id", relationship_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """Directed edge between nodes — never traverses or queries."""

    edge_id: str
    source_node_id: str
    target_node_id: str
    relationship_category: RelationshipCategory
    provenance: tuple[str, ...]
    relationship_id: str | None = None
    weight: Decimal | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        edge_id = _normalize_id(self.edge_id, field="edge_id")
        source = _normalize_id(self.source_node_id, field="source_node_id")
        target = _normalize_id(self.target_node_id, field="target_node_id")
        assert_relationship_category(self.relationship_category)
        if not self.provenance:
            msg = "missing provenance: GraphEdge requires provenance"
            raise KnowledgeGraphError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        relationship_id = (
            None
            if self.relationship_id is None
            else _normalize_id(self.relationship_id, field="relationship_id")
        )
        weight = (
            None
            if self.weight is None
            else require_decimal(self.weight, field="weight")
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "edge_id", edge_id)
        object.__setattr__(self, "source_node_id", source)
        object.__setattr__(self, "target_node_id", target)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "relationship_id", relationship_id)
        object.__setattr__(self, "weight", weight)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class EvidenceLink:
    """Cite-backed evidence association — never embeds evidence payloads."""

    link_id: str
    category: EvidenceLinkCategory
    source_node_id: str
    target_node_id: str
    provenance: tuple[str, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        link_id = _normalize_id(self.link_id, field="link_id")
        assert_evidence_link_category(self.category)
        source = _normalize_id(self.source_node_id, field="source_node_id")
        target = _normalize_id(self.target_node_id, field="target_node_id")
        if not self.provenance:
            msg = "missing provenance: EvidenceLink requires provenance"
            raise KnowledgeGraphError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "link_id", link_id)
        object.__setattr__(self, "source_node_id", source)
        object.__setattr__(self, "target_node_id", target)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class Lineage:
    """Ordered provenance chain — descriptive only."""

    lineage_id: str
    category: LineageCategory
    node_ids: tuple[str, ...]
    provenance: tuple[str, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        lineage_id = _normalize_id(self.lineage_id, field="lineage_id")
        assert_lineage_category(self.category)
        if not self.node_ids:
            msg = "broken references: Lineage requires at least one node_id"
            raise KnowledgeGraphError(msg)
        node_ids = tuple(
            _normalize_id(n, field="node_ids") for n in self.node_ids
        )
        if not self.provenance:
            msg = "missing provenance: Lineage requires provenance"
            raise KnowledgeGraphError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "lineage_id", lineage_id)
        object.__setattr__(self, "node_ids", node_ids)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class GraphSummary:
    """High-level graph summary — descriptive counts only."""

    node_count: int
    edge_count: int = 0
    relationship_count: int = 0
    evidence_link_count: int = 0
    lineage_count: int = 0
    limitation_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "node_count",
            "edge_count",
            "relationship_count",
            "evidence_link_count",
            "lineage_count",
        ):
            if getattr(self, name) < 0:
                msg = "counts must be >= 0"
                raise ValidationError(msg)
        limitations = tuple(
            n.strip() for n in self.limitation_notes if n.strip()
        )
        object.__setattr__(self, "limitation_notes", limitations)


@dataclass(frozen=True, slots=True)
class KnowledgeGraphReport:
    """Canonical immutable Knowledge Graph presentation / navigation snapshot."""

    graph_id: str
    summary: GraphSummary
    metadata: GraphMetadata
    as_of: str
    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    relationships: tuple[GraphRelationship, ...] = ()
    evidence_links: tuple[EvidenceLink, ...] = ()
    lineages: tuple[Lineage, ...] = ()
    analysis_refs: tuple[AnalysisReference, ...] = ()
    decision_refs: tuple[DecisionReference, ...] = ()
    industry_evidence_refs: tuple[IndustryEvidenceReference, ...] = ()
    comparison_refs: tuple[ComparisonReference, ...] = ()
    portfolio_refs: tuple[PortfolioReference, ...] = ()
    risk_refs: tuple[RiskReference, ...] = ()
    research_refs: tuple[ResearchReference, ...] = ()
    quantitative_risk_refs: tuple[QuantitativeRiskReference, ...] = ()
    recommendation_refs: tuple[RecommendationReference, ...] = ()
    workflow_refs: tuple[WorkflowReference, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        graph_id = _normalize_id(self.graph_id, field="graph_id")
        as_of = _non_empty(self.as_of, field="as_of")
        nodes = _unique_nodes(self.nodes)
        relationships = _unique_relationships(self.relationships)
        edges = _unique_edges(self.edges)
        evidence_links = _unique_evidence_links(self.evidence_links)
        lineages = _unique_lineages(self.lineages)
        node_ids = {n.node_id for n in nodes}
        relationship_ids = {r.relationship_id for r in relationships}
        _validate_edge_links(edges, node_ids, relationship_ids)
        _validate_evidence_links(evidence_links, node_ids)
        _validate_lineage_links(lineages, node_ids)
        _reject_duplicate_report_refs(
            analysis_refs=self.analysis_refs,
            decision_refs=self.decision_refs,
            industry_evidence_refs=self.industry_evidence_refs,
            comparison_refs=self.comparison_refs,
            portfolio_refs=self.portfolio_refs,
            risk_refs=self.risk_refs,
            research_refs=self.research_refs,
            quantitative_risk_refs=self.quantitative_risk_refs,
            recommendation_refs=self.recommendation_refs,
            workflow_refs=self.workflow_refs,
        )
        _require_anchor_refs(
            recommendation_refs=self.recommendation_refs,
            workflow_refs=self.workflow_refs,
        )
        limitations = tuple(n.strip() for n in self.limitations if n.strip())
        object.__setattr__(self, "graph_id", graph_id)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "relationships", relationships)
        object.__setattr__(self, "evidence_links", evidence_links)
        object.__setattr__(self, "lineages", lineages)
        object.__setattr__(self, "analysis_refs", tuple(self.analysis_refs))
        object.__setattr__(self, "decision_refs", tuple(self.decision_refs))
        object.__setattr__(
            self, "industry_evidence_refs", tuple(self.industry_evidence_refs)
        )
        object.__setattr__(self, "comparison_refs", tuple(self.comparison_refs))
        object.__setattr__(self, "portfolio_refs", tuple(self.portfolio_refs))
        object.__setattr__(self, "risk_refs", tuple(self.risk_refs))
        object.__setattr__(self, "research_refs", tuple(self.research_refs))
        object.__setattr__(
            self, "quantitative_risk_refs", tuple(self.quantitative_risk_refs)
        )
        object.__setattr__(
            self, "recommendation_refs", tuple(self.recommendation_refs)
        )
        object.__setattr__(self, "workflow_refs", tuple(self.workflow_refs))
        object.__setattr__(self, "limitations", limitations)


@dataclass(frozen=True, slots=True)
class GraphProfile:
    """Aggregate root — cites upstream reports; owns graph artifacts only."""

    identity: GraphIdentity
    metadata: GraphMetadata
    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    relationships: tuple[GraphRelationship, ...] = ()
    evidence_links: tuple[EvidenceLink, ...] = ()
    lineages: tuple[Lineage, ...] = ()
    summary: GraphSummary | None = None
    analysis_refs: tuple[AnalysisReference, ...] = ()
    decision_refs: tuple[DecisionReference, ...] = ()
    industry_evidence_refs: tuple[IndustryEvidenceReference, ...] = ()
    comparison_refs: tuple[ComparisonReference, ...] = ()
    portfolio_refs: tuple[PortfolioReference, ...] = ()
    risk_refs: tuple[RiskReference, ...] = ()
    research_refs: tuple[ResearchReference, ...] = ()
    quantitative_risk_refs: tuple[QuantitativeRiskReference, ...] = ()
    recommendation_refs: tuple[RecommendationReference, ...] = ()
    workflow_refs: tuple[WorkflowReference, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.identity is None:
            msg = "missing identity: GraphIdentity is required"
            raise KnowledgeGraphError(msg)
        nodes = _unique_nodes(self.nodes)
        relationships = _unique_relationships(self.relationships)
        edges = _unique_edges(self.edges)
        evidence_links = _unique_evidence_links(self.evidence_links)
        lineages = _unique_lineages(self.lineages)
        node_ids = {n.node_id for n in nodes}
        relationship_ids = {r.relationship_id for r in relationships}
        _validate_edge_links(edges, node_ids, relationship_ids)
        _validate_evidence_links(evidence_links, node_ids)
        _validate_lineage_links(lineages, node_ids)
        _reject_duplicate_report_refs(
            analysis_refs=self.analysis_refs,
            decision_refs=self.decision_refs,
            industry_evidence_refs=self.industry_evidence_refs,
            comparison_refs=self.comparison_refs,
            portfolio_refs=self.portfolio_refs,
            risk_refs=self.risk_refs,
            research_refs=self.research_refs,
            quantitative_risk_refs=self.quantitative_risk_refs,
            recommendation_refs=self.recommendation_refs,
            workflow_refs=self.workflow_refs,
        )
        _require_anchor_refs(
            recommendation_refs=self.recommendation_refs,
            workflow_refs=self.workflow_refs,
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "relationships", relationships)
        object.__setattr__(self, "evidence_links", evidence_links)
        object.__setattr__(self, "lineages", lineages)
        object.__setattr__(self, "analysis_refs", tuple(self.analysis_refs))
        object.__setattr__(self, "decision_refs", tuple(self.decision_refs))
        object.__setattr__(
            self, "industry_evidence_refs", tuple(self.industry_evidence_refs)
        )
        object.__setattr__(self, "comparison_refs", tuple(self.comparison_refs))
        object.__setattr__(self, "portfolio_refs", tuple(self.portfolio_refs))
        object.__setattr__(self, "risk_refs", tuple(self.risk_refs))
        object.__setattr__(self, "research_refs", tuple(self.research_refs))
        object.__setattr__(
            self, "quantitative_risk_refs", tuple(self.quantitative_risk_refs)
        )
        object.__setattr__(
            self, "recommendation_refs", tuple(self.recommendation_refs)
        )
        object.__setattr__(self, "workflow_refs", tuple(self.workflow_refs))
        object.__setattr__(self, "notes", notes)

    @property
    def graph_id(self) -> str:
        return self.identity.graph_id


def _unique_nodes(items: tuple[GraphNode, ...]) -> tuple[GraphNode, ...]:
    seen: set[str] = set()
    for item in items:
        if item.node_id in seen:
            msg = f"duplicate node ids: {item.node_id!r}"
            raise KnowledgeGraphError(msg)
        seen.add(item.node_id)
    return tuple(items)


def _unique_edges(items: tuple[GraphEdge, ...]) -> tuple[GraphEdge, ...]:
    seen: set[str] = set()
    for item in items:
        if item.edge_id in seen:
            msg = f"duplicate edge ids: {item.edge_id!r}"
            raise KnowledgeGraphError(msg)
        seen.add(item.edge_id)
    return tuple(items)


def _unique_relationships(
    items: tuple[GraphRelationship, ...],
) -> tuple[GraphRelationship, ...]:
    seen: set[str] = set()
    for item in items:
        if item.relationship_id in seen:
            msg = f"duplicate relationship ids: {item.relationship_id!r}"
            raise KnowledgeGraphError(msg)
        seen.add(item.relationship_id)
    return tuple(items)


def _unique_evidence_links(
    items: tuple[EvidenceLink, ...],
) -> tuple[EvidenceLink, ...]:
    seen: set[str] = set()
    for item in items:
        if item.link_id in seen:
            msg = f"duplicate evidence link ids: {item.link_id!r}"
            raise KnowledgeGraphError(msg)
        seen.add(item.link_id)
    return tuple(items)


def _unique_lineages(items: tuple[Lineage, ...]) -> tuple[Lineage, ...]:
    seen: set[str] = set()
    for item in items:
        if item.lineage_id in seen:
            msg = f"duplicate lineage ids: {item.lineage_id!r}"
            raise KnowledgeGraphError(msg)
        seen.add(item.lineage_id)
    return tuple(items)


def _validate_edge_links(
    edges: tuple[GraphEdge, ...],
    node_ids: set[str],
    relationship_ids: set[str],
) -> None:
    for edge in edges:
        if edge.source_node_id not in node_ids:
            msg = (
                f"broken references: edge {edge.edge_id!r} source "
                f"{edge.source_node_id!r} missing"
            )
            raise KnowledgeGraphError(msg)
        if edge.target_node_id not in node_ids:
            msg = (
                f"broken references: edge {edge.edge_id!r} target "
                f"{edge.target_node_id!r} missing"
            )
            raise KnowledgeGraphError(msg)
        if (
            edge.relationship_id is not None
            and edge.relationship_id not in relationship_ids
        ):
            msg = (
                f"broken references: edge {edge.edge_id!r} relationship "
                f"{edge.relationship_id!r} missing"
            )
            raise KnowledgeGraphError(msg)


def _validate_evidence_links(
    links: tuple[EvidenceLink, ...],
    node_ids: set[str],
) -> None:
    for link in links:
        if link.source_node_id not in node_ids:
            msg = (
                f"broken references: evidence link {link.link_id!r} source "
                f"{link.source_node_id!r} missing"
            )
            raise KnowledgeGraphError(msg)
        if link.target_node_id not in node_ids:
            msg = (
                f"broken references: evidence link {link.link_id!r} target "
                f"{link.target_node_id!r} missing"
            )
            raise KnowledgeGraphError(msg)


def _validate_lineage_links(
    lineages: tuple[Lineage, ...],
    node_ids: set[str],
) -> None:
    for lineage in lineages:
        for node_id in lineage.node_ids:
            if node_id not in node_ids:
                msg = (
                    f"broken references: lineage {lineage.lineage_id!r} "
                    f"references missing node {node_id!r}"
                )
                raise KnowledgeGraphError(msg)


def _reject_duplicate_report_refs(**groups: tuple[Any, ...]) -> None:
    for name, items in groups.items():
        seen_ids: set[str] = set()
        seen_reports: set[str] = set()
        for ref in items:
            if ref.id in seen_ids:
                msg = f"duplicate report references: {name} id {ref.id!r}"
                raise KnowledgeGraphError(msg)
            if ref.report_id in seen_reports:
                msg = (
                    f"duplicate report references: {name} report_id "
                    f"{ref.report_id!r}"
                )
                raise KnowledgeGraphError(msg)
            seen_ids.add(ref.id)
            seen_reports.add(ref.report_id)


def _require_anchor_refs(
    *,
    recommendation_refs: tuple[RecommendationReference, ...],
    workflow_refs: tuple[WorkflowReference, ...],
) -> None:
    if not recommendation_refs:
        msg = "broken references: at least one RecommendationReference required"
        raise KnowledgeGraphError(msg)
    if not workflow_refs:
        msg = "broken references: at least one WorkflowReference required"
        raise KnowledgeGraphError(msg)
