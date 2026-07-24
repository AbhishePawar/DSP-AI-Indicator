"""Knowledge Graph Reporter tests (I1.3) — presentation only."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from knowledge_graph import (
    AnalysisReference,
    AssemblyContext,
    GraphIdentity,
    GraphMetadata,
    IndustryEvidenceReference,
    KnowledgeGraphAssembler,
    KnowledgeGraphEngine,
    KnowledgeGraphError,
    KnowledgeGraphReport,
    KnowledgeGraphReporter,
    RecommendationReference,
    ReportingContext,
    ReportingStatus,
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


def _engine_result(*, with_optional: bool = True, graph_id: str = "dsp.kg.demo"):
    return KnowledgeGraphEngine().synthesize(
        _assemble(with_optional=with_optional, graph_id=graph_id)
    )


class TestReporterHappyPath:
    def test_from_engine_result(self) -> None:
        engine_result = _engine_result()
        result = KnowledgeGraphReporter().report(engine_result)
        assert result.status is ReportingStatus.COMPLETE
        assert result.metadata.graph_id == "dsp.kg.demo"
        assert result.metadata.node_count == engine_result.summary.node_count
        assert result.node_statistics.total == len(engine_result.nodes)
        assert result.edge_statistics.total == len(engine_result.edges)
        assert result.relationship_statistics.total == len(
            engine_result.relationships
        )
        assert result.evidence_link_statistics.total == len(
            engine_result.evidence_links
        )
        assert result.lineage_statistics.total == len(engine_result.lineages)
        assert result.validation_status.status == "valid"
        assert result.referenced_reports
        assert "nodes" in result.summary_sections
        assert any("presentation only" in n for n in result.report.limitations)
        assert result.metadata.method_id is not None

    def test_from_report(self) -> None:
        engine_result = _engine_result()
        result = KnowledgeGraphReporter().report(engine_result.report)
        assert result.status is ReportingStatus.COMPLETE
        assert result.report.nodes == engine_result.report.nodes
        assert result.report.edges == engine_result.report.edges

    def test_from_profile(self) -> None:
        engine_result = _engine_result()
        result = KnowledgeGraphReporter().report(engine_result.profile)
        assert result.metadata.graph_id == engine_result.graph_id
        assert result.node_statistics.total == len(engine_result.nodes)

    def test_preserves_ordering(self) -> None:
        engine_result = _engine_result()
        result = KnowledgeGraphReporter().report(engine_result)
        assert result.report.nodes == engine_result.report.nodes
        assert result.report.edges == engine_result.report.edges
        assert result.report.lineages == engine_result.report.lineages

    def test_does_not_mutate_source_report(self) -> None:
        engine_result = _engine_result()
        original_limitations = engine_result.report.limitations
        result = KnowledgeGraphReporter().report(engine_result)
        assert engine_result.report.limitations == original_limitations
        assert result.report is not engine_result.report
        assert len(result.report.limitations) >= len(original_limitations)

    def test_empty_assembler_skeleton(self) -> None:
        assembly = _assemble(with_optional=False)
        result = KnowledgeGraphReporter().report(assembly.report)
        assert result.status is ReportingStatus.EMPTY
        assert result.node_statistics.total == 0
        assert result.warnings

    def test_immutable(self) -> None:
        result = KnowledgeGraphReporter().report(_engine_result())
        with pytest.raises(AttributeError):
            result.summary_sections = ()  # type: ignore[misc]


class TestReporterValidation:
    def test_missing_inputs(self) -> None:
        with pytest.raises(KnowledgeGraphError, match="missing graph identity"):
            ReportingContext()

    def test_duplicate_report_sections(self) -> None:
        with pytest.raises(KnowledgeGraphError, match="duplicate report sections"):
            KnowledgeGraphReporter().report(
                ReportingContext(
                    engine_result=_engine_result(),
                    summary_sections=("overview", "Overview"),
                )
            )

    def test_identity_mismatch(self) -> None:
        engine_result = _engine_result()
        other = KnowledgeGraphReport(
            graph_id="dsp.kg.other",
            summary=engine_result.summary,
            metadata=_metadata(),
            as_of="2026-07-21",
            recommendation_refs=engine_result.report.recommendation_refs,
            workflow_refs=engine_result.report.workflow_refs,
        )
        with pytest.raises(KnowledgeGraphError, match="identity mismatch"):
            KnowledgeGraphReporter().report(
                ReportingContext(engine_result=engine_result, report=other)
            )

    def test_profile_mismatch(self) -> None:
        engine_result = _engine_result()
        other_profile = _engine_result(graph_id="dsp.kg.other").profile
        with pytest.raises(KnowledgeGraphError, match="reporter/report mismatch"):
            KnowledgeGraphReporter().report(
                ReportingContext(
                    engine_result=engine_result,
                    profile=other_profile,
                )
            )

    def test_report_many_duplicate(self) -> None:
        engine_result = _engine_result()
        with pytest.raises(KnowledgeGraphError, match="duplicate graph ids"):
            KnowledgeGraphReporter().report_many((engine_result, engine_result))


class TestReporterNoTopology:
    def test_reporter_forbids_construction_side_effects(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "knowledge_graph"
            / "reporter.py"
        ).read_text(encoding="utf-8")
        assert "KnowledgeGraphEngine().synthesize" not in source
        assert "KnowledgeGraphAssembler().assemble" not in source
        assert "neo4j" not in source.lower()
        assert "networkx" not in source.lower()
        assert "embedding" not in source.lower()

    def test_reporter_forbids_upstream_imports(self) -> None:
        path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "knowledge_graph"
            / "reporter.py"
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
            "portfolio",
            "risk",
            "research",
            "quantitative_risk",
            "workflow",
            "dsp_platform",
        }
        assert names & forbidden == set()
