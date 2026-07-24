"""Knowledge Graph Assembler tests (I1.1) — construction only."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from knowledge_graph import (
    AnalysisReference,
    AssemblyContext,
    AssemblyStatus,
    GraphIdentity,
    GraphMetadata,
    KnowledgeGraphAssembler,
    KnowledgeGraphError,
    RecommendationReference,
    WorkflowReference,
)


def _identity(graph_id: str = "dsp.kg.demo") -> GraphIdentity:
    return GraphIdentity(
        graph_id=graph_id,
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


def _ctx(
    *,
    graph_id: str = "dsp.kg.demo",
    with_optional: bool = False,
    recommendation_refs: tuple[RecommendationReference, ...] | None = None,
    workflow_refs: tuple[WorkflowReference, ...] | None = None,
) -> AssemblyContext:
    kwargs: dict = {
        "identity": _identity(graph_id),
        "metadata": _metadata(),
        "recommendation_refs": (
            (
                _ref(
                    RecommendationReference,
                    id_="dsp.kg.ref.recommendation.1",
                    report_id="dsp.recommendation.report.1",
                ),
            )
            if recommendation_refs is None
            else recommendation_refs
        ),
        "workflow_refs": (
            (
                _ref(
                    WorkflowReference,
                    id_="dsp.kg.ref.workflow.1",
                    report_id="dsp.workflow.report.1",
                ),
            )
            if workflow_refs is None
            else workflow_refs
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
    return AssemblyContext(**kwargs)  # type: ignore[arg-type]


class TestAssemblyHappyPath:
    def test_empty_skeleton_complete_with_optional(self) -> None:
        result = KnowledgeGraphAssembler().assemble(_ctx(with_optional=True))
        assert result.status is AssemblyStatus.COMPLETE
        assert result.profile.graph_id == "dsp.kg.demo"
        assert result.profile.nodes == ()
        assert result.profile.edges == ()
        assert result.profile.relationships == ()
        assert result.profile.evidence_links == ()
        assert result.profile.lineages == ()
        assert result.profile.summary is not None
        assert result.profile.summary.node_count == 0
        assert result.report.nodes == ()
        assert result.report.recommendation_refs
        assert result.report.workflow_refs
        assert any("skeleton" in note.lower() for note in result.report.limitations)

    def test_partial_without_optional_refs(self) -> None:
        result = KnowledgeGraphAssembler().assemble(_ctx(with_optional=False))
        assert result.status is AssemblyStatus.PARTIAL
        assert result.warnings
        assert result.profile.nodes == ()

    def test_immutable_output(self) -> None:
        result = KnowledgeGraphAssembler().assemble(_ctx(with_optional=True))
        with pytest.raises(AttributeError):
            result.report.nodes = ()  # type: ignore[misc]


class TestAssemblyValidation:
    def test_missing_recommendation_anchor(self) -> None:
        with pytest.raises(KnowledgeGraphError, match="Recommendation anchor"):
            KnowledgeGraphAssembler().assemble(_ctx(recommendation_refs=()))

    def test_missing_workflow_anchor(self) -> None:
        with pytest.raises(KnowledgeGraphError, match="Workflow anchor"):
            KnowledgeGraphAssembler().assemble(_ctx(workflow_refs=()))

    def test_duplicate_report_references(self) -> None:
        ref = _ref(
            RecommendationReference,
            id_="dsp.kg.ref.recommendation.1",
            report_id="dsp.recommendation.report.1",
        )
        with pytest.raises(KnowledgeGraphError, match="duplicate report references"):
            KnowledgeGraphAssembler().assemble(
                _ctx(recommendation_refs=(ref, ref))  # type: ignore[arg-type]
            )

    def test_duplicate_graph_ids_assemble_many(self) -> None:
        ctx = _ctx()
        with pytest.raises(KnowledgeGraphError, match="duplicate graph ids"):
            KnowledgeGraphAssembler().assemble_many((ctx, ctx))

    def test_assemble_many_distinct(self) -> None:
        results = KnowledgeGraphAssembler().assemble_many(
            (
                _ctx(graph_id="dsp.kg.a", with_optional=True),
                _ctx(graph_id="dsp.kg.b", with_optional=True),
            )
        )
        assert len(results) == 2
        assert results[0].profile.graph_id == "dsp.kg.a"
        assert results[1].profile.graph_id == "dsp.kg.b"


class TestAssemblerArchitecture:
    def test_assembler_forbids_upstream_imports(self) -> None:
        path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "knowledge_graph"
            / "assembler.py"
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
        }
        assert names & forbidden == set()
