"""AI Copilot Conversation Engine & Context Builder tests (J1.1)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from copilot import (
    ContextBuilder,
    ConversationEngine,
    ConversationEngineContext,
    ConversationRole,
    ConversationSession,
    ConversationState,
    ConversationStatus,
    ConversationTurn,
    CopilotError,
    CopilotIdentity,
    CopilotMetadata,
    KnowledgeGraphReference,
    RecommendationReference,
    UserIntent,
    UserIntentType,
    WorkflowReference,
    assert_legal_conversation_transition,
)


def _identity() -> CopilotIdentity:
    return CopilotIdentity(
        copilot_id="dsp.copilot.demo",
        copilot_name="Demo Copilot",
        created_at="2026-07-21T00:00:00Z",
    )


def _metadata() -> CopilotMetadata:
    return CopilotMetadata(as_of="2026-07-21", owner="platform")


def _ref(cls: type, *, id_: str, report_id: str) -> object:
    return cls(
        id=id_,
        report_id=report_id,
        version="1.0.0",
        digest="abcdef0123456789",
        status="complete",
        generated_at="2026-07-21T12:00:00Z",
    )


def _kg() -> KnowledgeGraphReference:
    return _ref(  # type: ignore[return-value]
        KnowledgeGraphReference,
        id_="dsp.copilot.ref.kg.1",
        report_id="dsp.kg.report.1",
    )


def _engine_context(**kwargs: object) -> ConversationEngineContext:
    base: dict = {
        "identity": _identity(),
        "metadata": _metadata(),
        "knowledge_graph_ref": _kg(),
        "user_text": "How are these reports connected in the knowledge graph?",
    }
    base.update(kwargs)
    return ConversationEngineContext(**base)  # type: ignore[arg-type]


class TestConversationHappyPath:
    def test_navigate_graph_routing(self) -> None:
        result = ConversationEngine().run(_engine_context())
        assert result.status is ConversationStatus.COMPLETE
        assert result.intent.intent_type is UserIntentType.NAVIGATE_GRAPH
        assert result.session.state is ConversationState.ACTIVE
        assert result.context_bundle.knowledge_graph_ref.id == _kg().id
        assert result.explanation_input.intent.intent_id == result.intent.intent_id
        assert result.conversation_context.focus_ref_id is not None

    def test_compare_companies_alias(self) -> None:
        result = ConversationEngine().run(
            _engine_context(user_text="Compare companies A and B")
        )
        assert result.intent.intent_type is UserIntentType.COMPARE_OUTCOMES

    def test_risk_query_alias(self) -> None:
        result = ConversationEngine().run(
            _engine_context(user_text="Risk query for this portfolio posture")
        )
        assert result.intent.intent_type is UserIntentType.SUMMARIZE_POSTURE

    def test_out_of_scope(self) -> None:
        result = ConversationEngine().run(
            _engine_context(user_text="Please buy 100 shares now")
        )
        assert result.status is ConversationStatus.OUT_OF_SCOPE
        assert result.intent.intent_type is UserIntentType.OUT_OF_SCOPE

    def test_clarify_on_empty(self) -> None:
        result = ConversationEngine().run(
            _engine_context(
                user_text="",
                intent=UserIntent(
                    intent_id="dsp.copilot.intent.clarify",
                    intent_type=UserIntentType.CLARIFY,
                    provenance=("test",),
                ),
            )
        )
        assert result.status is ConversationStatus.CLARIFY
        assert result.session.state is ConversationState.CLARIFYING

    def test_context_builder_digests(self) -> None:
        kg = KnowledgeGraphReference(
            id="dsp.copilot.ref.kg.1",
            report_id="dsp.kg.report.1",
            version="1.0.0",
            digest="aaaaaaaa11111111",
            status="complete",
            generated_at="2026-07-21T12:00:00Z",
        )
        bundle = ContextBuilder().build(
            bundle_id="dsp.copilot.bundle.test",
            knowledge_graph_ref=kg,
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
            workflow_refs=(
                WorkflowReference(
                    id="dsp.copilot.ref.wf.1",
                    report_id="dsp.workflow.report.1",
                    version="1.0.0",
                    digest="cccccccc33333333",
                    status="complete",
                    generated_at="2026-07-21T12:00:00Z",
                ),
            ),
        )
        assert len(bundle.digest_ids) == 3
        assert kg.digest in bundle.digest_ids

    def test_partial_without_optional_refs(self) -> None:
        result = ConversationEngine().run(
            _engine_context(user_text="Explain report posture and recommendation")
        )
        assert result.status is ConversationStatus.PARTIAL
        assert any("optional report" in w for w in result.warnings)

    def test_deterministic(self) -> None:
        engine = ConversationEngine()
        a = engine.run(_engine_context())
        b = engine.run(_engine_context())
        assert a.intent.intent_type is b.intent.intent_type
        assert a.context_bundle.digest_ids == b.context_bundle.digest_ids
        assert a.session.session_id == b.session.session_id


class TestConversationValidation:
    def test_missing_kg(self) -> None:
        with pytest.raises(TypeError):
            ConversationEngineContext(  # type: ignore[call-arg]
                identity=_identity(),
                metadata=_metadata(),
                user_text="hello",
            )

    def test_illegal_transition(self) -> None:
        with pytest.raises(CopilotError, match="illegal conversation transitions"):
            assert_legal_conversation_transition(
                ConversationState.COMPLETED, ConversationState.ACTIVE
            )

    def test_terminal_session_cannot_advance(self) -> None:
        session = ConversationSession(
            session_id="dsp.copilot.session.done",
            state=ConversationState.COMPLETED,
            provenance=("test",),
        )
        with pytest.raises(CopilotError, match="illegal conversation transitions"):
            ConversationEngine().run(
                _engine_context(
                    session=session,
                    user_text="How are these reports connected?",
                )
            )

    def test_turn_session_mismatch(self) -> None:
        session = ConversationSession(
            session_id="dsp.copilot.session.1",
            state=ConversationState.PENDING,
            provenance=("test",),
        )
        turn = ConversationTurn(
            turn_id="dsp.copilot.turn.1",
            session_id="dsp.copilot.session.other",
            role=ConversationRole.USER,
            sequence=0,
            content="hello",
            provenance=("test",),
            created_at="2026-07-21T12:00:00Z",
        )
        with pytest.raises(CopilotError, match="identity mismatch"):
            ConversationEngine().run(
                _engine_context(session=session, user_turn=turn, user_text="")
            )

    def test_run_many_duplicate(self) -> None:
        ctx = _engine_context()
        with pytest.raises(CopilotError, match="duplicate session ids"):
            ConversationEngine().run_many((ctx, ctx))

    def test_pending_to_active(self) -> None:
        session = ConversationSession(
            session_id="dsp.copilot.session.1",
            state=ConversationState.PENDING,
            provenance=("test",),
        )
        result = ConversationEngine().run(
            _engine_context(
                session=session,
                user_text="Explain report dsp.recommendation.report.1",
            )
        )
        assert result.session.state is ConversationState.ACTIVE
        assert result.intent.intent_type is UserIntentType.EXPLAIN_REPORT


class TestNoExplanationOrLLM:
    def test_conversation_module_forbids_llm(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "copilot"
            / "conversation.py"
        ).read_text(encoding="utf-8")
        assert "openai" not in source.lower()
        assert "anthropic" not in source.lower()
        assert "LanguageModelResult" not in source
        assert "Explanation(" not in source  # no Explanation generation
        assert "ExplanationInput" in source

    def test_no_upstream_imports(self) -> None:
        path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "copilot"
            / "conversation.py"
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
