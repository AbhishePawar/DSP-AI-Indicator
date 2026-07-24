"""AI Copilot Reporter tests (J1.3) — presentation only."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from copilot import (
    ConversationEngine,
    ConversationEngineContext,
    CopilotError,
    CopilotIdentity,
    CopilotMetadata,
    CopilotReporter,
    ExplanationEngine,
    KnowledgeGraphReference,
    RecommendationReference,
    ReportingContext,
    ResponseStatus,
)


def _identity(copilot_id: str = "dsp.copilot.demo") -> CopilotIdentity:
    return CopilotIdentity(
        copilot_id=copilot_id,
        copilot_name="Demo Copilot",
        created_at="2026-07-21T00:00:00Z",
    )


def _metadata() -> CopilotMetadata:
    return CopilotMetadata(as_of="2026-07-21", owner="platform")


def _kg() -> KnowledgeGraphReference:
    return KnowledgeGraphReference(
        id="dsp.copilot.ref.kg.1",
        report_id="dsp.kg.report.1",
        version="1.0.0",
        digest="aaaaaaaa11111111",
        status="complete",
        generated_at="2026-07-21T12:00:00Z",
    )


def _pipeline(*, copilot_id: str = "dsp.copilot.demo"):
    explanation_input = ConversationEngine().run(
        ConversationEngineContext(
            identity=_identity(copilot_id),
            metadata=_metadata(),
            knowledge_graph_ref=_kg(),
            user_text="Navigate graph: how connected are knowledge graph reports?",
            recommendation_refs=(
                RecommendationReference(
                    id="dsp.copilot.ref.rec.1",
                    report_id="dsp.recommendation.report.1",
                    version="1.0.0",
                    digest="bbbbbbbb22222222",
                    status="complete",
                    generated_at="2026-07-21T12:00:00Z",
                ),
            ),
        )
    ).explanation_input
    explanation_result = ExplanationEngine().explain(explanation_input)
    return explanation_input, explanation_result


class TestReporterHappyPath:
    def test_formats_copilot_response(self) -> None:
        explanation_input, explanation_result = _pipeline()
        result = CopilotReporter().report(
            ReportingContext(
                explanation_result=explanation_result,
                explanation_input=explanation_input,
                metadata=_metadata(),
            )
        )
        assert result.response.explanation is not None
        assert result.response.knowledge_graph_ref.id == _kg().id
        assert result.executive_summary
        assert result.key_reasons
        assert result.risks
        assert result.supporting_evidence
        assert result.citations
        assert result.provenance
        assert result.validation_status.status == "valid"
        assert result.statistics.total > 0
        assert any("presentation only" in n for n in result.response.limitations)
        assert result.status in (
            ResponseStatus.COMPLETE,
            ResponseStatus.PARTIAL,
        )

    def test_preserves_explanation_identity(self) -> None:
        explanation_input, explanation_result = _pipeline()
        result = CopilotReporter().report(
            ReportingContext(
                explanation_result=explanation_result,
                explanation_input=explanation_input,
            )
        )
        assert (
            result.response.explanation.explanation_id
            == explanation_result.explanation.explanation_id
        )
        assert result.response.intent is explanation_input.intent

    def test_immutable(self) -> None:
        explanation_input, explanation_result = _pipeline()
        result = CopilotReporter().report(
            ReportingContext(
                explanation_result=explanation_result,
                explanation_input=explanation_input,
            )
        )
        with pytest.raises(AttributeError):
            result.citations = ()  # type: ignore[misc]

    def test_refusal_presentation(self) -> None:
        explanation_input = ConversationEngine().run(
            ConversationEngineContext(
                identity=_identity(),
                metadata=_metadata(),
                knowledge_graph_ref=_kg(),
                user_text="Please buy 100 shares now",
            )
        ).explanation_input
        explanation_result = ExplanationEngine().explain(explanation_input)
        result = CopilotReporter().report(
            ReportingContext(
                explanation_result=explanation_result,
                explanation_input=explanation_input,
            )
        )
        assert result.status is ResponseStatus.REFUSED


class TestReporterValidation:
    def test_duplicate_sections(self) -> None:
        explanation_input, explanation_result = _pipeline()
        with pytest.raises(CopilotError, match="duplicate report sections"):
            CopilotReporter().report(
                ReportingContext(
                    explanation_result=explanation_result,
                    explanation_input=explanation_input,
                    summary_sections=("overview", "Overview"),
                )
            )

    def test_report_many_duplicate(self) -> None:
        explanation_input, explanation_result = _pipeline()
        ctx = ReportingContext(
            explanation_result=explanation_result,
            explanation_input=explanation_input,
        )
        with pytest.raises(CopilotError, match="duplicate copilot ids"):
            CopilotReporter().report_many((ctx, ctx))


class TestReporterNoSideEffects:
    def test_reporter_forbids_generation(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "copilot"
            / "reporter.py"
        ).read_text(encoding="utf-8")
        assert "ExplanationEngine().explain" not in source
        assert "LanguageModelPort" not in source
        assert "openai" not in source.lower()
        assert "ConversationEngine().run" not in source

    def test_no_upstream_imports(self) -> None:
        path = (
            Path(__file__).resolve().parents[1] / "src" / "copilot" / "reporter.py"
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
            "knowledge_graph",
            "recommendation",
            "workflow",
            "openai",
            "anthropic",
        }
        assert names & forbidden == set()
