"""AI Copilot domain model tests (J1.0)."""

from __future__ import annotations

import pytest
from core.exceptions import ValidationError

from copilot import (
    ContextBundle,
    ConversationContext,
    ConversationRole,
    ConversationSession,
    ConversationState,
    ConversationTurn,
    CopilotError,
    CopilotIdentity,
    CopilotMetadata,
    CopilotProfile,
    CopilotResponse,
    CopilotSummary,
    Explanation,
    ExplanationType,
    KnowledgeGraphReference,
    LanguageModelRequest,
    LanguageModelResult,
    LanguageModelStatus,
    RecommendationReference,
    ResponseStatus,
    UserIntent,
    UserIntentType,
    WorkflowReference,
    assert_unique_copilot_ids,
    assert_unique_session_ids,
    assert_unique_turn_ids,
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


def _kg_ref() -> KnowledgeGraphReference:
    return _ref(  # type: ignore[return-value]
        KnowledgeGraphReference,
        id_="dsp.copilot.ref.kg.1",
        report_id="dsp.kg.report.1",
    )


class TestConstruction:
    def test_profile_and_response(self) -> None:
        kg = _kg_ref()
        intent = UserIntent(
            intent_id="dsp.copilot.intent.1",
            intent_type=UserIntentType.NAVIGATE_GRAPH,
            provenance=("copilot.models",),
            raw_text="How are these reports connected?",
        )
        turn = ConversationTurn(
            turn_id="dsp.copilot.turn.1",
            session_id="dsp.copilot.session.1",
            role=ConversationRole.USER,
            sequence=0,
            content="How are these reports connected?",
            provenance=("copilot.models",),
            created_at="2026-07-21T12:00:00Z",
            intent_id=intent.intent_id,
        )
        session = ConversationSession(
            session_id="dsp.copilot.session.1",
            state=ConversationState.ACTIVE,
            provenance=("copilot.models",),
            turns=(turn,),
            context=ConversationContext(
                context_id="dsp.copilot.context.1",
                as_of="2026-07-21",
                provenance=("copilot.models",),
                focus_ref_id=kg.id,
            ),
            created_at="2026-07-21T12:00:00Z",
        )
        bundle = ContextBundle(
            bundle_id="dsp.copilot.bundle.1",
            knowledge_graph_ref=kg,
            provenance=("copilot.models",),
            digest_ids=(kg.digest,),
            recommendation_refs=(
                _ref(  # type: ignore[arg-type]
                    RecommendationReference,
                    id_="dsp.copilot.ref.rec.1",
                    report_id="dsp.recommendation.report.1",
                ),
            ),
            workflow_refs=(
                _ref(  # type: ignore[arg-type]
                    WorkflowReference,
                    id_="dsp.copilot.ref.wf.1",
                    report_id="dsp.workflow.report.1",
                ),
            ),
        )
        explanation = Explanation(
            explanation_id="dsp.copilot.explanation.1",
            explanation_type=ExplanationType.HYBRID,
            narrative="Reports are linked via the knowledge graph.",
            provenance=("copilot.models",),
            evidence_refs=(kg.digest,),
            is_generated_narrative=True,
        )
        profile = CopilotProfile(
            identity=_identity(),
            metadata=_metadata(),
            knowledge_graph_ref=kg,
            session=session,
            intents=(intent,),
            context_bundles=(bundle,),
            explanations=(explanation,),
            summary=CopilotSummary(
                turn_count=1,
                explanation_count=1,
                citation_count=1,
                session_count=1,
            ),
        )
        response = CopilotResponse(
            copilot_id=profile.copilot_id,
            summary=profile.summary,  # type: ignore[arg-type]
            metadata=_metadata(),
            as_of="2026-07-21",
            status=ResponseStatus.COMPLETE,
            knowledge_graph_ref=kg,
            session_id=session.session_id,
            intent=intent,
            context_bundle=bundle,
            explanation=explanation,
        )
        assert profile.copilot_id == "dsp.copilot.demo"
        assert response.status is ResponseStatus.COMPLETE
        assert response.knowledge_graph_ref.id == kg.id

    def test_language_model_contracts(self) -> None:
        request = LanguageModelRequest(
            request_id="dsp.copilot.lm.req.1",
            intent_class=UserIntentType.EXPLAIN_REPORT,
            prompt_parts=("Explain the cited report.",),
            context_digest_ids=("abcdef0123456789",),
            provenance=("copilot.models",),
            constraints=("cite-only",),
        )
        result = LanguageModelResult(
            result_id="dsp.copilot.lm.res.1",
            status=LanguageModelStatus.COMPLETE,
            provenance=("copilot.models",),
            narrative_text="The report cites supporting evidence.",
            cited_digest_ids=("abcdef0123456789",),
            model_label="stub.v1",
        )
        assert request.intent_class is UserIntentType.EXPLAIN_REPORT
        assert result.model_label == "stub.v1"

    def test_refusal_explanation_without_evidence(self) -> None:
        explanation = Explanation(
            explanation_id="dsp.copilot.explanation.refuse",
            explanation_type=ExplanationType.REFUSAL,
            narrative="Out of scope for trading instructions.",
            provenance=("copilot.models",),
            limitations=("out_of_scope",),
        )
        assert explanation.evidence_refs == ()


class TestValidation:
    def test_missing_knowledge_graph_ref(self) -> None:
        with pytest.raises(TypeError):
            CopilotProfile(  # type: ignore[call-arg]
                identity=_identity(),
                metadata=_metadata(),
            )

    def test_duplicate_turn_ids(self) -> None:
        turn = ConversationTurn(
            turn_id="dsp.copilot.turn.dup",
            session_id="dsp.copilot.session.1",
            role=ConversationRole.USER,
            sequence=0,
            content="hello",
            provenance=("copilot.models",),
            created_at="2026-07-21T12:00:00Z",
        )
        with pytest.raises(CopilotError, match="duplicate turn ids"):
            ConversationSession(
                session_id="dsp.copilot.session.1",
                state=ConversationState.ACTIVE,
                provenance=("copilot.models",),
                turns=(turn, turn),
            )

    def test_turn_session_mismatch(self) -> None:
        turn = ConversationTurn(
            turn_id="dsp.copilot.turn.1",
            session_id="dsp.copilot.session.other",
            role=ConversationRole.USER,
            sequence=0,
            content="hello",
            provenance=("copilot.models",),
            created_at="2026-07-21T12:00:00Z",
        )
        with pytest.raises(CopilotError, match="broken references"):
            ConversationSession(
                session_id="dsp.copilot.session.1",
                state=ConversationState.ACTIVE,
                provenance=("copilot.models",),
                turns=(turn,),
            )

    def test_explanation_requires_evidence(self) -> None:
        with pytest.raises(CopilotError, match="evidence_refs"):
            Explanation(
                explanation_id="dsp.copilot.explanation.bad",
                explanation_type=ExplanationType.NARRATIVE,
                narrative="Invented claim.",
                provenance=("copilot.models",),
            )

    def test_missing_provenance(self) -> None:
        with pytest.raises(CopilotError, match="missing provenance"):
            UserIntent(
                intent_id="dsp.copilot.intent.1",
                intent_type=UserIntentType.CLARIFY,
                provenance=(),
            )

    def test_invalid_digest(self) -> None:
        with pytest.raises(ValidationError, match="digest"):
            KnowledgeGraphReference(
                id="dsp.copilot.ref.kg.bad",
                report_id="dsp.kg.report.1",
                version="1.0.0",
                digest="short",
                status="complete",
                generated_at="2026-07-21T12:00:00Z",
            )

    def test_unique_helpers(self) -> None:
        assert_unique_turn_ids(("a", "b"))
        assert_unique_session_ids(("s1", "s2"))
        assert_unique_copilot_ids(("c1", "c2"))
        with pytest.raises(CopilotError, match="duplicate session ids"):
            assert_unique_session_ids(("s1", "s1"))

    def test_immutable(self) -> None:
        identity = _identity()
        with pytest.raises(AttributeError):
            identity.copilot_id = "x"  # type: ignore[misc]

    def test_lm_complete_requires_content(self) -> None:
        with pytest.raises(CopilotError, match="COMPLETE requires"):
            LanguageModelResult(
                result_id="dsp.copilot.lm.res.empty",
                status=LanguageModelStatus.COMPLETE,
                provenance=("copilot.models",),
            )
