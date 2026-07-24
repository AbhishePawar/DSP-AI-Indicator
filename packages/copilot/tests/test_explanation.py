"""AI Copilot Explanation Engine tests (J1.2)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from copilot import (
    ConfidenceLevel,
    ContextBuilder,
    ConversationEngine,
    ConversationEngineContext,
    CopilotError,
    CopilotIdentity,
    CopilotMetadata,
    EvidenceValidator,
    ExplanationDraft,
    ExplanationEngine,
    ExplanationStatus,
    ExplanationType,
    KnowledgeGraphReference,
    LanguageModelRequest,
    LanguageModelResult,
    LanguageModelStatus,
    RecommendationReference,
    UserIntentType,
)


def _identity() -> CopilotIdentity:
    return CopilotIdentity(
        copilot_id="dsp.copilot.demo",
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


def _explanation_input(
    *, user_text: str = "Navigate graph: how connected are knowledge graph reports?"
):
    conversation = ConversationEngine().run(
        ConversationEngineContext(
            identity=_identity(),
            metadata=_metadata(),
            knowledge_graph_ref=_kg(),
            user_text=user_text,
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
    )
    return conversation.explanation_input


class _StubLM:
    def __init__(self, result: LanguageModelResult | None = None, *, fail: bool = False):
        self._result = result
        self._fail = fail

    def invoke(self, request: LanguageModelRequest) -> LanguageModelResult:
        del request
        if self._fail:
            raise RuntimeError("provider down")
        assert self._result is not None
        return self._result


class TestExplanationHappyPath:
    def test_deterministic_fallback(self) -> None:
        result = ExplanationEngine().explain(_explanation_input())
        assert result.status in (
            ExplanationStatus.COMPLETE,
            ExplanationStatus.PARTIAL,
        )
        assert result.executive_summary
        assert result.key_reasons
        assert result.risks
        assert result.supporting_evidence
        assert result.citations
        assert result.provenance
        assert result.confidence in (
            ConfidenceLevel.LOW,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.HIGH,
        )
        assert result.explanation.explanation_type is ExplanationType.EVIDENCE_SUMMARY
        assert any("deterministic fallback" in w for w in result.warnings)

    def test_with_language_model(self) -> None:
        inp = _explanation_input()
        digests = inp.context_bundle.digest_ids
        stub = _StubLM(
            LanguageModelResult(
                result_id="dsp.copilot.lm.res.1",
                status=LanguageModelStatus.COMPLETE,
                provenance=("test.stub",),
                narrative_text="Hybrid cite-only narrative.",
                structured_sections=(
                    "Executive summary from LM.",
                    "Reason one.",
                ),
                cited_digest_ids=digests[:1],
                model_label="stub.v1",
            )
        )
        result = ExplanationEngine(language_model=stub).explain(inp)
        assert result.explanation.explanation_type is ExplanationType.HYBRID
        assert result.explanation.is_generated_narrative is True
        assert "Hybrid cite-only narrative." in result.explanation.narrative

    def test_lm_unavailable_falls_back(self) -> None:
        result = ExplanationEngine(language_model=_StubLM(fail=True)).explain(
            _explanation_input()
        )
        assert any("failed" in w.lower() or "fallback" in w for w in result.warnings)
        assert result.explanation.explanation_type is ExplanationType.EVIDENCE_SUMMARY

    def test_refusal(self) -> None:
        result = ExplanationEngine().explain(
            _explanation_input(user_text="Please buy 100 shares now")
        )
        assert result.status is ExplanationStatus.REFUSED
        assert result.explanation.explanation_type is ExplanationType.REFUSAL
        assert result.confidence is ConfidenceLevel.NONE

    def test_clarify(self) -> None:
        # Force clarify via pre-routed conversation with ambiguous text
        from copilot import UserIntent

        conversation = ConversationEngine().run(
            ConversationEngineContext(
                identity=_identity(),
                metadata=_metadata(),
                knowledge_graph_ref=_kg(),
                intent=UserIntent(
                    intent_id="dsp.copilot.intent.clarify",
                    intent_type=UserIntentType.CLARIFY,
                    provenance=("test",),
                ),
            )
        )
        result = ExplanationEngine().explain(conversation.explanation_input)
        assert result.status is ExplanationStatus.CLARIFY
        assert result.explanation.explanation_type is ExplanationType.CLARIFICATION

    def test_sections_present(self) -> None:
        result = ExplanationEngine().explain(_explanation_input())
        assert result.executive_summary
        assert len(result.key_reasons) >= 1
        assert len(result.risks) >= 1
        assert len(result.supporting_evidence) >= 1
        assert len(result.citations) >= 1


class TestEvidenceValidator:
    def test_duplicate_citations_in_draft(self) -> None:
        bundle = ContextBuilder().build(
            bundle_id="dsp.copilot.bundle.v",
            knowledge_graph_ref=_kg(),
        )
        draft = ExplanationDraft(
            executive_summary="Summary",
            key_reasons=("r",),
            risks=("risk",),
            supporting_evidence=("e",),
            claim_evidence_links=(("claim", _kg().digest),),
            citations=(_kg().digest, _kg().digest),
            narrative="Narrative text.",
            explanation_type=ExplanationType.EVIDENCE_SUMMARY,
            is_generated_narrative=False,
        )
        with pytest.raises(CopilotError, match="duplicate citations"):
            EvidenceValidator().validate_draft(
                draft,
                allowed_digests=frozenset(bundle.digest_ids),
                require_evidence=True,
            )

    def test_unsupported_claim_digest(self) -> None:
        draft = ExplanationDraft(
            executive_summary="Summary",
            key_reasons=("r",),
            risks=("risk",),
            supporting_evidence=("e",),
            claim_evidence_links=(("claim", "zzzzzzzz99999999"),),
            citations=("zzzzzzzz99999999",),
            narrative="Narrative text.",
            explanation_type=ExplanationType.EVIDENCE_SUMMARY,
            is_generated_narrative=False,
        )
        with pytest.raises(CopilotError, match="unsupported claims"):
            EvidenceValidator().validate_draft(
                draft,
                allowed_digests=frozenset({_kg().digest}),
                require_evidence=True,
            )

    def test_empty_narrative(self) -> None:
        with pytest.raises(CopilotError, match="empty explanation"):
            EvidenceValidator().validate_draft(
                ExplanationDraft(
                    executive_summary="Summary",
                    key_reasons=(),
                    risks=(),
                    supporting_evidence=(),
                    claim_evidence_links=(),
                    citations=(),
                    narrative="   ",
                    explanation_type=ExplanationType.CLARIFICATION,
                    is_generated_narrative=False,
                ),
                allowed_digests=frozenset(),
                require_evidence=False,
            )


class TestExplanationNoSideEffects:
    def test_no_vendor_sdks(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "copilot"
            / "explanation.py"
        ).read_text(encoding="utf-8")
        assert "openai" not in source.lower()
        assert "anthropic" not in source.lower()
        assert "quantize" not in source
        assert "neo4j" not in source.lower()

    def test_no_upstream_imports(self) -> None:
        path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "copilot"
            / "explanation.py"
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
            "valuation",
            "openai",
        }
        assert names & forbidden == set()
