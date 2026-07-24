"""Knowledge Graph Engine tests (I1.2) — deterministic topology only."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from knowledge_graph import (
    AnalysisReference,
    AssemblyContext,
    EngineContext,
    EngineStatus,
    GraphIdentity,
    GraphMetadata,
    IndustryEvidenceReference,
    KnowledgeGraphAssembler,
    KnowledgeGraphEngine,
    KnowledgeGraphError,
    LineageCategory,
    NodeCategory,
    RecommendationReference,
    RelationshipCategory,
    WorkflowReference,
)


def _identity(graph_id: str = "dsp.kg.demo") -> GraphIdentity:
    return GraphIdentity(
        graph_id=graph_id,
        graph_name="Demo Graph",
        created_at="2026-07-21T00:00:00Z",
    )


def _metadata() -> GraphMetadata:
    return GraphMetadata(corpus_id="dsp.kg.corpus.demo", as_of="2026-07-21")


def _ref(cls: type, *, id_: str, report_id: str) -> object:
    return cls(
        id=id_,
        report_id=report_id,
        version="1.0.0",
        digest="abcdef0123456789",
        status="complete",
        generated_at="2026-07-21T12:00:00Z",
    )


def _assemble(*, with_optional: bool = True, graph_id: str = "dsp.kg.demo"):
    kwargs: dict = {
        "identity": _identity(graph_id),
        "metadata": _metadata(),
        "recommendation_refs": (
            _ref(
                RecommendationReference,
                id_="dsp.kg.ref.recommendation.1",
                report_id="dsp.recommendation.report.1",
            ),
        ),
        "workflow_refs": (
            _ref(
                WorkflowReference,
                id_="dsp.kg.ref.workflow.1",
                report_id="dsp.workflow.report.1",
            ),
        ),
    }
    if with_optional:
        kwargs["analysis_refs"] = (
            _ref(
                AnalysisReference,
                id_="dsp.kg.ref.analysis.1",
                report_id="dsp.analysis.report.1",
            ),
        )
        kwargs["industry_evidence_refs"] = (
            _ref(
                IndustryEvidenceReference,
                id_="dsp.kg.ref.ief.1",
                report_id="dsp.ief.report.1",
            ),
        )
    return KnowledgeGraphAssembler().assemble(AssemblyContext(**kwargs))  # type: ignore[arg-type]


class TestEngineHappyPath:
    def test_full_topology(self) -> None:
        assembly = _assemble(with_optional=True)
        result = KnowledgeGraphEngine().synthesize(assembly)
        assert result.status is EngineStatus.COMPLETE
        assert result.summary.node_count == 4  # analysis, evidence, rec, wf
        assert result.nodes
        assert result.edges
        assert result.relationships
        assert result.evidence_links
        assert result.lineages
        cats = {n.category for n in result.nodes}
        assert NodeCategory.RECOMMENDATION in cats
        assert NodeCategory.WORKFLOW in cats
        assert NodeCategory.EVIDENCE in cats
        assert NodeCategory.REPORT in cats
        assert any(
            e.relationship_category is RelationshipCategory.EXECUTED_BY
            for e in result.edges
        )
        assert any(
            e.relationship_category is RelationshipCategory.DERIVES_FROM
            for e in result.edges
        )
        assert any(lin.category is LineageCategory.EXECUTION for lin in result.lineages)
        assert any(lin.category is LineageCategory.EVIDENCE for lin in result.lineages)

    def test_anchors_only_partial(self) -> None:
        result = KnowledgeGraphEngine().synthesize(_assemble(with_optional=False))
        assert result.status is EngineStatus.PARTIAL
        assert result.summary.node_count == 2
        assert result.warnings
        assert result.evidence_links == ()

    def test_deterministic(self) -> None:
        assembly = _assemble(with_optional=True)
        a = KnowledgeGraphEngine().synthesize(assembly)
        b = KnowledgeGraphEngine().synthesize(_assemble(with_optional=True))
        assert a.report.nodes == b.report.nodes
        assert a.report.edges == b.report.edges
        assert a.report.lineages == b.report.lineages

    def test_immutable(self) -> None:
        result = KnowledgeGraphEngine().synthesize(_assemble())
        with pytest.raises(AttributeError):
            result.report.nodes = ()  # type: ignore[misc]


class TestEngineValidation:
    def test_identity_mismatch(self) -> None:
        assembly = _assemble()
        other_assembly = _assemble(graph_id="dsp.kg.other")
        with pytest.raises(KnowledgeGraphError, match="identity mismatch"):
            KnowledgeGraphEngine().synthesize(
                EngineContext(
                    assembly=assembly,
                    profile=other_assembly.profile,
                )
            )

    def test_synthesize_many_duplicate(self) -> None:
        assembly = _assemble()
        ctx = EngineContext(assembly=assembly)
        with pytest.raises(KnowledgeGraphError, match="duplicate graph ids"):
            KnowledgeGraphEngine().synthesize_many((ctx, ctx))


class TestEngineArchitecture:
    def test_engine_forbids_upstream_imports(self) -> None:
        path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "knowledge_graph"
            / "engine.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name.split(".", 1)[0])
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                names.add(node.module.split(".", 1)[0])
        forbidden = {
            "orchestration",
            "recommendation",
            "workflow",
            "portfolio",
            "risk",
            "research",
            "quantitative_risk",
            "dsp_platform",
            "neo4j",
            "networkx",
        }
        assert names & forbidden == set()
