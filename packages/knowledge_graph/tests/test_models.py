"""Knowledge Graph domain model tests (I1.0)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from core.exceptions import ValidationError

from knowledge_graph import (
    AnalysisReference,
    EvidenceLink,
    EvidenceLinkCategory,
    GraphEdge,
    GraphIdentity,
    GraphMetadata,
    GraphNode,
    GraphProfile,
    GraphRelationship,
    GraphSummary,
    KnowledgeGraphError,
    KnowledgeGraphReport,
    Lineage,
    LineageCategory,
    NodeCategory,
    RecommendationReference,
    RelationshipCategory,
    WorkflowReference,
    assert_unique_graph_ids,
)


def _identity() -> GraphIdentity:
    return GraphIdentity(
        graph_id="dsp.kg.demo",
        graph_name="Demo Graph",
        created_at="2026-07-21T00:00:00Z",
    )


def _metadata() -> GraphMetadata:
    return GraphMetadata(
        corpus_id="dsp.kg.corpus.demo",
        as_of="2026-07-21",
        owner="platform",
    )


def _ref(
    cls: type,
    *,
    id_: str,
    report_id: str,
) -> object:
    return cls(
        id=id_,
        report_id=report_id,
        version="1.0.0",
        digest="abcdef0123456789",
        status="complete",
        generated_at="2026-07-21T12:00:00Z",
    )


def _anchors() -> tuple[RecommendationReference, WorkflowReference]:
    return (
        _ref(  # type: ignore[return-value]
            RecommendationReference,
            id_="dsp.kg.ref.recommendation.1",
            report_id="dsp.recommendation.report.1",
        ),
        _ref(  # type: ignore[return-value]
            WorkflowReference,
            id_="dsp.kg.ref.workflow.1",
            report_id="dsp.workflow.report.1",
        ),
    )


def _node(
    *,
    node_id: str = "dsp.kg.node.security.aaa",
    category: NodeCategory = NodeCategory.SECURITY,
) -> GraphNode:
    return GraphNode(
        node_id=node_id,
        category=category,
        label=node_id.rsplit(".", 1)[-1],
        provenance=("knowledge_graph.models",),
    )


class TestConstruction:
    def test_profile_and_report(self) -> None:
        recommendation, workflow = _anchors()
        nodes = (
            _node(),
            _node(node_id="dsp.kg.node.report.rec", category=NodeCategory.REPORT),
            _node(node_id="dsp.kg.node.report.wf", category=NodeCategory.WORKFLOW),
        )
        relationship = GraphRelationship(
            relationship_id="dsp.kg.rel.references",
            category=RelationshipCategory.REFERENCES,
            title="References",
            provenance=("knowledge_graph.models",),
        )
        edge = GraphEdge(
            edge_id="dsp.kg.edge.1",
            source_node_id="dsp.kg.node.security.aaa",
            target_node_id="dsp.kg.node.report.rec",
            relationship_category=RelationshipCategory.REFERENCES,
            relationship_id=relationship.relationship_id,
            weight=Decimal("1"),
            provenance=("knowledge_graph.models",),
        )
        evidence = EvidenceLink(
            link_id="dsp.kg.evidence.1",
            category=EvidenceLinkCategory.DIRECT,
            source_node_id="dsp.kg.node.security.aaa",
            target_node_id="dsp.kg.node.report.rec",
            provenance=("knowledge_graph.models",),
        )
        lineage = Lineage(
            lineage_id="dsp.kg.lineage.1",
            category=LineageCategory.REPORT,
            node_ids=(
                "dsp.kg.node.report.wf",
                "dsp.kg.node.report.rec",
            ),
            provenance=("knowledge_graph.models",),
        )
        profile = GraphProfile(
            identity=_identity(),
            metadata=_metadata(),
            nodes=nodes,
            edges=(edge,),
            relationships=(relationship,),
            evidence_links=(evidence,),
            lineages=(lineage,),
            summary=GraphSummary(
                node_count=3,
                edge_count=1,
                relationship_count=1,
                evidence_link_count=1,
                lineage_count=1,
            ),
            recommendation_refs=(recommendation,),
            workflow_refs=(workflow,),
            analysis_refs=(
                _ref(  # type: ignore[arg-type]
                    AnalysisReference,
                    id_="dsp.kg.ref.analysis.1",
                    report_id="dsp.analysis.report.1",
                ),
            ),
        )
        assert profile.graph_id == "dsp.kg.demo"

        report = KnowledgeGraphReport(
            graph_id="dsp.kg.demo",
            summary=GraphSummary(node_count=3, edge_count=1),
            metadata=_metadata(),
            as_of="2026-07-21",
            nodes=nodes,
            edges=(edge,),
            relationships=(relationship,),
            evidence_links=(evidence,),
            lineages=(lineage,),
            recommendation_refs=(recommendation,),
            workflow_refs=(workflow,),
            limitations=("Contracts only — no assembler.",),
        )
        assert report.graph_id == "dsp.kg.demo"
        with pytest.raises(AttributeError):
            report.nodes = ()  # type: ignore[misc]


class TestValidation:
    def test_duplicate_graph_ids(self) -> None:
        assert_unique_graph_ids(("a", "b"))
        with pytest.raises(KnowledgeGraphError, match="duplicate graph ids"):
            assert_unique_graph_ids(("dsp.kg.a", "DSP.KG.A"))

    def test_duplicate_node_ids(self) -> None:
        recommendation, workflow = _anchors()
        node = _node()
        with pytest.raises(KnowledgeGraphError, match="duplicate node ids"):
            GraphProfile(
                identity=_identity(),
                metadata=_metadata(),
                nodes=(node, node),
                recommendation_refs=(recommendation,),
                workflow_refs=(workflow,),
            )

    def test_duplicate_edge_ids(self) -> None:
        recommendation, workflow = _anchors()
        nodes = (
            _node(),
            _node(node_id="dsp.kg.node.b", category=NodeCategory.ENTITY),
        )
        edge = GraphEdge(
            edge_id="dsp.kg.edge.1",
            source_node_id="dsp.kg.node.security.aaa",
            target_node_id="dsp.kg.node.b",
            relationship_category=RelationshipCategory.RELATED_TO,
            provenance=("p",),
        )
        with pytest.raises(KnowledgeGraphError, match="duplicate edge ids"):
            GraphProfile(
                identity=_identity(),
                metadata=_metadata(),
                nodes=nodes,
                edges=(edge, edge),
                recommendation_refs=(recommendation,),
                workflow_refs=(workflow,),
            )

    def test_broken_edge_reference(self) -> None:
        recommendation, workflow = _anchors()
        with pytest.raises(KnowledgeGraphError, match="broken references"):
            GraphProfile(
                identity=_identity(),
                metadata=_metadata(),
                nodes=(_node(),),
                edges=(
                    GraphEdge(
                        edge_id="dsp.kg.edge.1",
                        source_node_id="dsp.kg.node.security.aaa",
                        target_node_id="dsp.kg.node.missing",
                        relationship_category=RelationshipCategory.REFERENCES,
                        provenance=("p",),
                    ),
                ),
                recommendation_refs=(recommendation,),
                workflow_refs=(workflow,),
            )

    def test_missing_anchor_refs(self) -> None:
        with pytest.raises(KnowledgeGraphError, match="RecommendationReference"):
            GraphProfile(
                identity=_identity(),
                metadata=_metadata(),
                workflow_refs=(
                    _ref(  # type: ignore[arg-type]
                        WorkflowReference,
                        id_="dsp.kg.ref.workflow.1",
                        report_id="dsp.workflow.report.1",
                    ),
                ),
            )

    def test_missing_provenance(self) -> None:
        with pytest.raises(KnowledgeGraphError, match="missing provenance"):
            GraphNode(
                node_id="dsp.kg.node.x",
                category=NodeCategory.ENTITY,
                label="x",
                provenance=(),
            )

    def test_decimal_policy_rejects_float(self) -> None:
        with pytest.raises(ValidationError, match="decimal.Decimal"):
            GraphEdge(
                edge_id="dsp.kg.edge.1",
                source_node_id="a",
                target_node_id="b",
                relationship_category=RelationshipCategory.RELATED_TO,
                provenance=("p",),
                weight=1.5,  # type: ignore[arg-type]
            )

    def test_broken_digest(self) -> None:
        with pytest.raises(ValidationError, match="broken references"):
            WorkflowReference(
                id="dsp.kg.ref.wf",
                report_id="dsp.workflow.report.x",
                version="1",
                digest="short",
                status="complete",
                generated_at="2026-07-21T00:00:00Z",
            )

    def test_duplicate_report_references(self) -> None:
        recommendation = _ref(
            RecommendationReference,
            id_="dsp.kg.ref.recommendation.1",
            report_id="dsp.recommendation.report.1",
        )
        duplicate = _ref(
            RecommendationReference,
            id_="dsp.kg.ref.recommendation.2",
            report_id="dsp.recommendation.report.1",
        )
        workflow = _ref(
            WorkflowReference,
            id_="dsp.kg.ref.workflow.1",
            report_id="dsp.workflow.report.1",
        )
        with pytest.raises(KnowledgeGraphError, match="duplicate report references"):
            GraphProfile(
                identity=_identity(),
                metadata=_metadata(),
                recommendation_refs=(recommendation, duplicate),  # type: ignore[arg-type]
                workflow_refs=(workflow,),  # type: ignore[arg-type]
            )
