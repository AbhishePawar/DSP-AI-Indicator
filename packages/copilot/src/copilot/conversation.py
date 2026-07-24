"""AI Copilot Conversation Engine & Context Builder (J1.1).

Understands user intent, validates conversation state, and assembles immutable
context for the Explanation Engine. Never generates explanations, invokes
LLMs, persists, or performs business calculations.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from core.exceptions import ValidationError

from copilot.enums import (
    ConversationRole,
    ConversationState,
    ConversationStatus,
    UserIntentType,
)
from copilot.exceptions import CopilotError
from copilot.models import (
    ContextBundle,
    ConversationContext,
    ConversationSession,
    ConversationTurn,
    CopilotIdentity,
    CopilotMetadata,
    UserIntent,
)
from copilot.refs import (
    AnalysisReference,
    ComparisonReference,
    DecisionReference,
    IndustryEvidenceReference,
    KnowledgeGraphReference,
    PortfolioReference,
    QuantitativeRiskReference,
    RecommendationReference,
    ResearchReference,
    RiskReference,
    WorkflowReference,
)
from copilot.validation import (
    assert_legal_conversation_transition,
    assert_unique_session_ids,
    assert_user_intent_type,
)

__all__ = [
    "ContextBuilder",
    "ConversationEngine",
    "ConversationEngineContext",
    "ConversationResult",
    "ExplanationInput",
]

_PROVENANCE = ("copilot.conversation", "dsp.copilot.method.conversation.v1")

# Deterministic keyword → frozen UserIntentType routing (no LLM).
# Mission aliases (COMPARE_COMPANIES, VALUATION_QUERY, …) map onto the
# frozen J0.0A / J1.0 taxonomy only — additive aliases, not new conclusions.
_INTENT_KEYWORDS: tuple[tuple[UserIntentType, tuple[str, ...]], ...] = (
    (
        UserIntentType.OUT_OF_SCOPE,
        (
            "buy",
            "sell",
            "place order",
            "oms",
            "execute trade",
            "trading instruction",
        ),
    ),
    (
        UserIntentType.COMPARE_OUTCOMES,
        (
            "compare companies",
            "compare company",
            "compare peers",
            "peer comparison",
            "compare outcomes",
            "comparison",
        ),
    ),
    (
        UserIntentType.TRACE_EVIDENCE,
        (
            "trace evidence",
            "evidence link",
            "supporting evidence",
            "what evidence",
        ),
    ),
    (
        UserIntentType.NAVIGATE_GRAPH,
        (
            "knowledge graph",
            "how connected",
            "lineage",
            "navigate graph",
            "graph connection",
        ),
    ),
    (
        UserIntentType.SUMMARIZE_POSTURE,
        (
            "risk query",
            "risk posture",
            "portfolio query",
            "recommendation query",
            "summarize posture",
            "what should",
            "valuation query",
            "intrinsic value",
        ),
    ),
    (
        UserIntentType.EXPLAIN_REPORT,
        (
            "explain report",
            "explain the",
            "workflow query",
            "what does the report",
            "summarize report",
        ),
    ),
    (
        UserIntentType.CLARIFY,
        (
            "clarification required",
            "what do you mean",
            "clarify",
            "not sure",
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class ConversationEngineContext:
    """Inputs for deterministic conversation routing and context assembly.

    Consumes session / turn / intent / citations only. Domain
    ``ConversationContext`` is produced as an output artifact.
    """

    identity: CopilotIdentity
    metadata: CopilotMetadata
    knowledge_graph_ref: KnowledgeGraphReference
    session: ConversationSession | None = None
    user_text: str = ""
    user_turn: ConversationTurn | None = None
    intent: UserIntent | None = None
    conversation_context: ConversationContext | None = None
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
            msg = "identity is required"
            raise ValidationError(msg)
        if self.metadata is None:
            msg = "metadata is required"
            raise ValidationError(msg)
        if self.knowledge_graph_ref is None:
            msg = "KnowledgeGraphReference is required"
            raise ValidationError(msg)
        object.__setattr__(self, "user_text", (self.user_text or "").strip())
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
        object.__setattr__(
            self, "notes", tuple(n.strip() for n in self.notes if n.strip())
        )


@dataclass(frozen=True, slots=True)
class ExplanationInput:
    """Prepared immutable input for Explanation Engine (J1.2) — no generation."""

    intent: UserIntent
    context_bundle: ContextBundle
    conversation_context: ConversationContext
    session_id: str
    copilot_id: str
    as_of: str
    provenance: tuple[str, ...] = _PROVENANCE
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "provenance", tuple(self.provenance))
        object.__setattr__(
            self, "notes", tuple(n.strip() for n in self.notes if n.strip())
        )


@dataclass(frozen=True, slots=True)
class ConversationResult:
    """Conversation engine output — routing + assembled context only."""

    session: ConversationSession
    intent: UserIntent
    conversation_context: ConversationContext
    context_bundle: ContextBundle
    explanation_input: ExplanationInput
    status: ConversationStatus
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", tuple(self.warnings))


class ContextBuilder:
    """Assembles immutable ``ContextBundle`` from citations — no LLM."""

    def build(
        self,
        *,
        bundle_id: str,
        knowledge_graph_ref: KnowledgeGraphReference,
        analysis_refs: tuple[AnalysisReference, ...] = (),
        decision_refs: tuple[DecisionReference, ...] = (),
        industry_evidence_refs: tuple[IndustryEvidenceReference, ...] = (),
        comparison_refs: tuple[ComparisonReference, ...] = (),
        portfolio_refs: tuple[PortfolioReference, ...] = (),
        risk_refs: tuple[RiskReference, ...] = (),
        research_refs: tuple[ResearchReference, ...] = (),
        quantitative_risk_refs: tuple[QuantitativeRiskReference, ...] = (),
        recommendation_refs: tuple[RecommendationReference, ...] = (),
        workflow_refs: tuple[WorkflowReference, ...] = (),
        notes: tuple[str, ...] = (),
    ) -> ContextBundle:
        """Normalize citations into a ContextBundle; require Knowledge Graph."""
        if knowledge_graph_ref is None:
            msg = "broken KnowledgeGraph references: KnowledgeGraphReference required"
            raise CopilotError(msg)
        digest_ids = self._collect_digest_ids(
            knowledge_graph_ref=knowledge_graph_ref,
            analysis_refs=analysis_refs,
            decision_refs=decision_refs,
            industry_evidence_refs=industry_evidence_refs,
            comparison_refs=comparison_refs,
            portfolio_refs=portfolio_refs,
            risk_refs=risk_refs,
            research_refs=research_refs,
            quantitative_risk_refs=quantitative_risk_refs,
            recommendation_refs=recommendation_refs,
            workflow_refs=workflow_refs,
        )
        return ContextBundle(
            bundle_id=bundle_id,
            knowledge_graph_ref=knowledge_graph_ref,
            provenance=_PROVENANCE,
            digest_ids=digest_ids,
            analysis_refs=analysis_refs,
            decision_refs=decision_refs,
            industry_evidence_refs=industry_evidence_refs,
            comparison_refs=comparison_refs,
            portfolio_refs=portfolio_refs,
            risk_refs=risk_refs,
            research_refs=research_refs,
            quantitative_risk_refs=quantitative_risk_refs,
            recommendation_refs=recommendation_refs,
            workflow_refs=workflow_refs,
            notes=notes,
        )

    def _collect_digest_ids(self, **groups: object) -> tuple[str, ...]:
        digests: list[str] = []
        kg = groups.get("knowledge_graph_ref")
        if isinstance(kg, KnowledgeGraphReference):
            digests.append(kg.digest)
        for key, value in groups.items():
            if key == "knowledge_graph_ref":
                continue
            if not isinstance(value, tuple):
                continue
            for ref in value:
                digests.append(ref.digest)
        # Preserve first-seen order.
        return tuple(dict.fromkeys(digests))


class ConversationEngine:
    """Canonical conversation router and context assembler.

    Deterministic intent routing and state validation only — never explains
    or invokes LanguageModelPort.
    """

    def __init__(self, context_builder: ContextBuilder | None = None) -> None:
        self._builder = context_builder or ContextBuilder()

    def validate_inputs(self, context: ConversationEngineContext) -> None:
        """Reject invalid conversation / citation inputs."""
        if context.identity is None or not context.identity.copilot_id:
            msg = "missing CopilotIdentity"
            raise CopilotError(msg)
        if context.metadata is None or not context.metadata.as_of:
            msg = "missing CopilotMetadata"
            raise CopilotError(msg)
        if context.knowledge_graph_ref is None:
            msg = "broken KnowledgeGraph references: KnowledgeGraphReference required"
            raise CopilotError(msg)
        self._validate_ref(context.knowledge_graph_ref)
        for name, group in (
            ("analysis_refs", context.analysis_refs),
            ("decision_refs", context.decision_refs),
            ("industry_evidence_refs", context.industry_evidence_refs),
            ("comparison_refs", context.comparison_refs),
            ("portfolio_refs", context.portfolio_refs),
            ("risk_refs", context.risk_refs),
            ("research_refs", context.research_refs),
            ("quantitative_risk_refs", context.quantitative_risk_refs),
            ("recommendation_refs", context.recommendation_refs),
            ("workflow_refs", context.workflow_refs),
        ):
            self._validate_ref_group(name, group)

        if context.session is not None:
            if context.user_turn is not None:
                if context.user_turn.session_id != context.session.session_id:
                    msg = (
                        "identity mismatch: user_turn session_id "
                        f"{context.user_turn.session_id!r} vs session "
                        f"{context.session.session_id!r}"
                    )
                    raise CopilotError(msg)
            if context.conversation_context is not None:
                # Prior context must share as_of with metadata when both present.
                if (
                    context.conversation_context.as_of
                    and context.metadata.as_of
                    and context.conversation_context.as_of != context.metadata.as_of
                ):
                    msg = (
                        "identity mismatch: ConversationContext as_of "
                        f"{context.conversation_context.as_of!r} vs metadata "
                        f"{context.metadata.as_of!r}"
                    )
                    raise CopilotError(msg)

        if context.intent is not None:
            assert_user_intent_type(context.intent.intent_type)

        if (
            not context.user_text
            and context.user_turn is None
            and context.intent is None
        ):
            msg = "missing user input: user_text, user_turn, or intent required"
            raise CopilotError(msg)

    def run(self, context: ConversationEngineContext) -> ConversationResult:
        """Route intent, advance session, assemble context + ExplanationInput."""
        self.validate_inputs(context)
        warnings: list[str] = []

        intent = self._resolve_intent(context)
        target_state = self._target_state(intent.intent_type)
        session = self._advance_session(context, intent=intent, target_state=target_state)

        conversation_context = self._build_conversation_context(
            context=context,
            session=session,
            intent=intent,
        )
        context_bundle = self._builder.build(
            bundle_id=f"dsp.copilot.bundle.{session.session_id}.{intent.intent_id}",
            knowledge_graph_ref=context.knowledge_graph_ref,
            analysis_refs=context.analysis_refs,
            decision_refs=context.decision_refs,
            industry_evidence_refs=context.industry_evidence_refs,
            comparison_refs=context.comparison_refs,
            portfolio_refs=context.portfolio_refs,
            risk_refs=context.risk_refs,
            research_refs=context.research_refs,
            quantitative_risk_refs=context.quantitative_risk_refs,
            recommendation_refs=context.recommendation_refs,
            workflow_refs=context.workflow_refs,
            notes=context.notes,
        )
        self._reject_duplicate_bundle_against_session(session, context_bundle)

        if not self._has_optional_report_refs(context) and intent.intent_type in (
            UserIntentType.EXPLAIN_REPORT,
            UserIntentType.SUMMARIZE_POSTURE,
            UserIntentType.COMPARE_OUTCOMES,
            UserIntentType.TRACE_EVIDENCE,
        ):
            warnings.append(
                "optional report references absent; context cites Knowledge Graph only."
            )
        if intent.intent_type in (UserIntentType.UNKNOWN, UserIntentType.CLARIFY):
            warnings.append("intent requires clarification before explanation.")
        if intent.intent_type is UserIntentType.OUT_OF_SCOPE:
            warnings.append("intent out of scope — explanation should refuse.")

        explanation_input = ExplanationInput(
            intent=intent,
            context_bundle=context_bundle,
            conversation_context=conversation_context,
            session_id=session.session_id,
            copilot_id=context.identity.copilot_id,
            as_of=context.metadata.as_of,
            notes=context.notes,
        )
        status = self._status(intent.intent_type, warnings)
        return ConversationResult(
            session=session,
            intent=intent,
            conversation_context=conversation_context,
            context_bundle=context_bundle,
            explanation_input=explanation_input,
            status=status,
            warnings=tuple(warnings),
        )

    def run_many(
        self, contexts: tuple[ConversationEngineContext, ...]
    ) -> tuple[ConversationResult, ...]:
        """Run many conversations; reject duplicate session identities."""
        session_ids: list[str] = []
        for ctx in contexts:
            if ctx.session is not None:
                session_ids.append(ctx.session.session_id)
            else:
                session_ids.append(f"dsp.copilot.session.{ctx.identity.copilot_id}")
        assert_unique_session_ids(tuple(session_ids))
        return tuple(self.run(ctx) for ctx in contexts)

    def detect_intent(self, text: str) -> UserIntentType:
        """Deterministic keyword intent detection — never invokes an LLM."""
        cleaned = (text or "").strip().lower()
        if not cleaned:
            return UserIntentType.CLARIFY
        for intent_type, keywords in _INTENT_KEYWORDS:
            if any(keyword in cleaned for keyword in keywords):
                return intent_type
        return UserIntentType.UNKNOWN

    def _resolve_intent(self, context: ConversationEngineContext) -> UserIntent:
        if context.intent is not None:
            return context.intent
        raw = context.user_text
        if not raw and context.user_turn is not None:
            raw = context.user_turn.content
        intent_type = self.detect_intent(raw)
        intent_id = (
            f"dsp.copilot.intent.{context.identity.copilot_id}."
            f"{intent_type.value}"
        )
        target_ref_ids: tuple[str, ...] = ()
        if context.conversation_context and context.conversation_context.focus_ref_id:
            target_ref_ids = (context.conversation_context.focus_ref_id,)
        return UserIntent(
            intent_id=intent_id,
            intent_type=intent_type,
            provenance=_PROVENANCE,
            raw_text=raw or None,
            target_ref_ids=target_ref_ids,
        )

    def _target_state(self, intent_type: UserIntentType) -> ConversationState:
        if intent_type in (UserIntentType.CLARIFY, UserIntentType.UNKNOWN):
            return ConversationState.CLARIFYING
        if intent_type is UserIntentType.OUT_OF_SCOPE:
            return ConversationState.ACTIVE
        return ConversationState.ACTIVE

    def _advance_session(
        self,
        context: ConversationEngineContext,
        *,
        intent: UserIntent,
        target_state: ConversationState,
    ) -> ConversationSession:
        if context.session is None:
            session_id = f"dsp.copilot.session.{context.identity.copilot_id}"
            turns = self._initial_turns(session_id, context, intent)
            return ConversationSession(
                session_id=session_id,
                state=target_state,
                provenance=_PROVENANCE,
                turns=turns,
                context=None,
                created_at=context.metadata.as_of,
            )

        source = context.session.state
        if source is not target_state:
            assert_legal_conversation_transition(source, target_state)

        turns = list(context.session.turns)
        if context.user_turn is not None:
            if any(t.turn_id == context.user_turn.turn_id for t in turns):
                msg = f"duplicate turn ids: {context.user_turn.turn_id!r}"
                raise CopilotError(msg)
            turns.append(context.user_turn)
        elif context.user_text:
            sequence = len(turns)
            turns.append(
                ConversationTurn(
                    turn_id=(
                        f"dsp.copilot.turn.{context.session.session_id}.{sequence}"
                    ),
                    session_id=context.session.session_id,
                    role=ConversationRole.USER,
                    sequence=sequence,
                    content=context.user_text,
                    provenance=_PROVENANCE,
                    created_at=context.metadata.as_of,
                    intent_id=intent.intent_id,
                )
            )
        return replace(
            context.session,
            state=target_state,
            turns=tuple(turns),
            provenance=_PROVENANCE,
        )

    def _initial_turns(
        self,
        session_id: str,
        context: ConversationEngineContext,
        intent: UserIntent,
    ) -> tuple[ConversationTurn, ...]:
        if context.user_turn is not None:
            if context.user_turn.session_id != session_id:
                # Align turn to new session via replace when creating session.
                turn = replace(
                    context.user_turn,
                    session_id=session_id,
                    intent_id=intent.intent_id,
                )
                return (turn,)
            return (context.user_turn,)
        if context.user_text:
            return (
                ConversationTurn(
                    turn_id=f"dsp.copilot.turn.{session_id}.0",
                    session_id=session_id,
                    role=ConversationRole.USER,
                    sequence=0,
                    content=context.user_text,
                    provenance=_PROVENANCE,
                    created_at=context.metadata.as_of,
                    intent_id=intent.intent_id,
                ),
            )
        return ()

    def _build_conversation_context(
        self,
        *,
        context: ConversationEngineContext,
        session: ConversationSession,
        intent: UserIntent,
    ) -> ConversationContext:
        focus = context.knowledge_graph_ref.id
        if context.conversation_context and context.conversation_context.focus_ref_id:
            focus = context.conversation_context.focus_ref_id
        elif intent.target_ref_ids:
            focus = intent.target_ref_ids[0]
        return ConversationContext(
            context_id=f"dsp.copilot.context.{session.session_id}",
            as_of=context.metadata.as_of,
            provenance=_PROVENANCE,
            focus_ref_id=focus,
            focus_label=intent.intent_type.value,
            constraints=tuple(
                dict.fromkeys(
                    (
                        f"intent:{intent.intent_type.value}",
                        "cite-only",
                        "no-llm",
                    )
                )
            ),
            notes=context.notes,
        )

    def _reject_duplicate_bundle_against_session(
        self, session: ConversationSession, bundle: ContextBundle
    ) -> None:
        # Session notes may carry prior bundle ids in future; for now ensure
        # bundle_id is non-empty and deterministic (validated by ContextBundle).
        del session
        if not bundle.bundle_id:
            msg = "duplicate context bundles: empty bundle_id"
            raise CopilotError(msg)

    def _has_optional_report_refs(self, context: ConversationEngineContext) -> bool:
        return any(
            (
                context.analysis_refs,
                context.decision_refs,
                context.industry_evidence_refs,
                context.comparison_refs,
                context.portfolio_refs,
                context.risk_refs,
                context.research_refs,
                context.quantitative_risk_refs,
                context.recommendation_refs,
                context.workflow_refs,
            )
        )

    def _status(
        self, intent_type: UserIntentType, warnings: list[str]
    ) -> ConversationStatus:
        if intent_type is UserIntentType.OUT_OF_SCOPE:
            return ConversationStatus.OUT_OF_SCOPE
        if intent_type in (UserIntentType.CLARIFY, UserIntentType.UNKNOWN):
            return ConversationStatus.CLARIFY
        if warnings:
            return ConversationStatus.PARTIAL
        return ConversationStatus.COMPLETE

    def _validate_ref_group(self, name: str, refs: tuple[object, ...]) -> None:
        seen_ids: set[str] = set()
        seen_reports: set[str] = set()
        for ref in refs:
            self._validate_ref(ref)
            rid = getattr(ref, "id")
            report_id = getattr(ref, "report_id")
            if rid in seen_ids:
                msg = f"duplicate report references: {name} id {rid!r}"
                raise CopilotError(msg)
            if report_id in seen_reports:
                msg = f"duplicate report references: {name} report_id {report_id!r}"
                raise CopilotError(msg)
            seen_ids.add(rid)
            seen_reports.add(report_id)

    def _validate_ref(self, ref: object) -> None:
        for field in ("id", "report_id", "version", "digest", "status", "generated_at"):
            value = getattr(ref, field, None)
            if not value or not str(value).strip():
                msg = f"broken references: missing {field}"
                raise CopilotError(msg)
        digest = str(getattr(ref, "digest"))
        if len(digest.strip()) < 8:
            msg = "broken KnowledgeGraph references: digest invalid"
            raise CopilotError(msg)
