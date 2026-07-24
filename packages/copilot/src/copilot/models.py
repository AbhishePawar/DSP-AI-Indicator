"""AI Copilot domain models — contracts only (J1.0).

Immutable value objects and aggregates. No conversation orchestration,
explanation generation, LLM invocation, or persistence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.exceptions import ValidationError

from copilot.enums import (
    ConversationRole,
    ConversationState,
    ExplanationType,
    LanguageModelStatus,
    ResponseStatus,
    UserIntentType,
)
from copilot.exceptions import CopilotError
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
    _normalize_id,
)
from copilot.validation import (
    assert_conversation_role,
    assert_conversation_state,
    assert_explanation_type,
    assert_language_model_status,
    assert_response_status,
    assert_unique_turn_ids,
    assert_user_intent_type,
)

__all__ = [
    "ContextBundle",
    "ConversationContext",
    "ConversationSession",
    "ConversationTurn",
    "CopilotIdentity",
    "CopilotMetadata",
    "CopilotProfile",
    "CopilotResponse",
    "CopilotSummary",
    "Explanation",
    "LanguageModelRequest",
    "LanguageModelResult",
    "UserIntent",
]


def _non_empty(text: str, *, field: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        msg = f"{field} must not be empty"
        raise ValidationError(msg)
    return cleaned


@dataclass(frozen=True, slots=True)
class CopilotIdentity:
    """Canonical identity of an AI Copilot profile / assistant."""

    copilot_id: str
    copilot_name: str
    created_at: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        copilot_id = _normalize_id(self.copilot_id, field="copilot_id")
        name = _non_empty(self.copilot_name, field="copilot_name")
        created_at = (
            None if self.created_at is None else self.created_at.strip() or None
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "copilot_id", copilot_id)
        object.__setattr__(self, "copilot_name", name)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class CopilotMetadata:
    """Descriptive copilot metadata — not a business score."""

    as_of: str
    owner: str | None = None
    tags: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        as_of = _non_empty(self.as_of, field="as_of")
        owner = None if self.owner is None else self.owner.strip() or None
        tags = tuple(t.strip() for t in self.tags if t.strip())
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "owner", owner)
        object.__setattr__(self, "tags", tags)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class ConversationContext:
    """Active session scope — as-of / focus / constraints only."""

    context_id: str
    as_of: str
    provenance: tuple[str, ...]
    focus_ref_id: str | None = None
    focus_label: str | None = None
    constraints: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        context_id = _normalize_id(self.context_id, field="context_id")
        as_of = _non_empty(self.as_of, field="as_of")
        if not self.provenance:
            msg = "missing provenance: ConversationContext requires provenance"
            raise CopilotError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        focus_ref_id = (
            None
            if self.focus_ref_id is None
            else _normalize_id(self.focus_ref_id, field="focus_ref_id")
        )
        focus_label = (
            None if self.focus_label is None else self.focus_label.strip() or None
        )
        constraints = tuple(c.strip() for c in self.constraints if c.strip())
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "context_id", context_id)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "focus_ref_id", focus_ref_id)
        object.__setattr__(self, "focus_label", focus_label)
        object.__setattr__(self, "constraints", constraints)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class UserIntent:
    """Structured intent classification — routing only, never a market call."""

    intent_id: str
    intent_type: UserIntentType
    provenance: tuple[str, ...]
    raw_text: str | None = None
    target_ref_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        intent_id = _normalize_id(self.intent_id, field="intent_id")
        assert_user_intent_type(self.intent_type)
        if not self.provenance:
            msg = "missing provenance: UserIntent requires provenance"
            raise CopilotError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        raw_text = None if self.raw_text is None else self.raw_text.strip() or None
        target_ref_ids = tuple(
            _normalize_id(r, field="target_ref_ids") for r in self.target_ref_ids
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "intent_id", intent_id)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "raw_text", raw_text)
        object.__setattr__(self, "target_ref_ids", target_ref_ids)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    """Immutable user / assistant / system turn record."""

    turn_id: str
    session_id: str
    role: ConversationRole
    sequence: int
    content: str
    provenance: tuple[str, ...]
    created_at: str
    intent_id: str | None = None
    response_id: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        turn_id = _normalize_id(self.turn_id, field="turn_id")
        session_id = _normalize_id(self.session_id, field="session_id")
        assert_conversation_role(self.role)
        if self.sequence < 0:
            msg = "sequence must be >= 0"
            raise ValidationError(msg)
        content = _non_empty(self.content, field="content")
        if not self.provenance:
            msg = "missing provenance: ConversationTurn requires provenance"
            raise CopilotError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        created_at = _non_empty(self.created_at, field="created_at")
        intent_id = (
            None
            if self.intent_id is None
            else _normalize_id(self.intent_id, field="intent_id")
        )
        response_id = (
            None
            if self.response_id is None
            else _normalize_id(self.response_id, field="response_id")
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "turn_id", turn_id)
        object.__setattr__(self, "session_id", session_id)
        object.__setattr__(self, "content", content)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "intent_id", intent_id)
        object.__setattr__(self, "response_id", response_id)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class ConversationSession:
    """Ordered conversation lifecycle container."""

    session_id: str
    state: ConversationState
    provenance: tuple[str, ...]
    turns: tuple[ConversationTurn, ...] = ()
    context: ConversationContext | None = None
    created_at: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        session_id = _normalize_id(self.session_id, field="session_id")
        assert_conversation_state(self.state)
        if not self.provenance:
            msg = "missing provenance: ConversationSession requires provenance"
            raise CopilotError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        turns = _unique_turns(self.turns)
        for turn in turns:
            if turn.session_id != session_id:
                msg = (
                    f"broken references: turn {turn.turn_id!r} session_id "
                    f"{turn.session_id!r} does not match session {session_id!r}"
                )
                raise CopilotError(msg)
        created_at = (
            None if self.created_at is None else self.created_at.strip() or None
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "session_id", session_id)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "turns", turns)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class ContextBundle:
    """Assembled citation pack for one turn / explanation — cite-only."""

    bundle_id: str
    knowledge_graph_ref: KnowledgeGraphReference
    provenance: tuple[str, ...]
    digest_ids: tuple[str, ...] = ()
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
        bundle_id = _normalize_id(self.bundle_id, field="bundle_id")
        if self.knowledge_graph_ref is None:
            msg = "broken references: KnowledgeGraphReference required"
            raise CopilotError(msg)
        if not self.provenance:
            msg = "missing provenance: ContextBundle requires provenance"
            raise CopilotError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        digest_ids = tuple(
            _normalize_id(d, field="digest_ids") for d in self.digest_ids
        )
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
            knowledge_graph_refs=(self.knowledge_graph_ref,),
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "bundle_id", bundle_id)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "digest_ids", digest_ids)
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


@dataclass(frozen=True, slots=True)
class Explanation:
    """Evidence-backed explanation — distinguishes evidence from narrative."""

    explanation_id: str
    explanation_type: ExplanationType
    narrative: str
    provenance: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    is_generated_narrative: bool = True
    limitations: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        explanation_id = _normalize_id(self.explanation_id, field="explanation_id")
        assert_explanation_type(self.explanation_type)
        narrative = _non_empty(self.narrative, field="narrative")
        if not self.provenance:
            msg = "missing provenance: Explanation requires provenance"
            raise CopilotError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        evidence_refs = tuple(
            _normalize_id(r, field="evidence_refs") for r in self.evidence_refs
        )
        if (
            self.explanation_type
            not in (ExplanationType.CLARIFICATION, ExplanationType.REFUSAL)
            and not evidence_refs
        ):
            msg = (
                "broken references: Explanation requires evidence_refs "
                "unless clarification or refusal"
            )
            raise CopilotError(msg)
        limitations = tuple(n.strip() for n in self.limitations if n.strip())
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "explanation_id", explanation_id)
        object.__setattr__(self, "narrative", narrative)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "evidence_refs", evidence_refs)
        object.__setattr__(self, "limitations", limitations)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class CopilotSummary:
    """High-level copilot summary — descriptive counts only."""

    turn_count: int = 0
    explanation_count: int = 0
    citation_count: int = 0
    session_count: int = 0
    limitation_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "turn_count",
            "explanation_count",
            "citation_count",
            "session_count",
        ):
            if getattr(self, name) < 0:
                msg = "counts must be >= 0"
                raise ValidationError(msg)
        limitations = tuple(
            n.strip() for n in self.limitation_notes if n.strip()
        )
        object.__setattr__(self, "limitation_notes", limitations)


@dataclass(frozen=True, slots=True)
class LanguageModelRequest:
    """Provider-neutral LM request contract — no vendor schemas."""

    request_id: str
    intent_class: UserIntentType
    prompt_parts: tuple[str, ...]
    context_digest_ids: tuple[str, ...]
    provenance: tuple[str, ...]
    constraints: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        request_id = _normalize_id(self.request_id, field="request_id")
        assert_user_intent_type(self.intent_class)
        if not self.prompt_parts:
            msg = "LanguageModelRequest requires at least one prompt_part"
            raise CopilotError(msg)
        prompt_parts = tuple(
            _non_empty(p, field="prompt_parts") for p in self.prompt_parts
        )
        context_digest_ids = tuple(
            _normalize_id(d, field="context_digest_ids")
            for d in self.context_digest_ids
        )
        if not self.provenance:
            msg = "missing provenance: LanguageModelRequest requires provenance"
            raise CopilotError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        constraints = tuple(c.strip() for c in self.constraints if c.strip())
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "request_id", request_id)
        object.__setattr__(self, "prompt_parts", prompt_parts)
        object.__setattr__(self, "context_digest_ids", context_digest_ids)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "constraints", constraints)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class LanguageModelResult:
    """Provider-neutral LM result contract — opaque model_label only."""

    result_id: str
    status: LanguageModelStatus
    provenance: tuple[str, ...]
    narrative_text: str | None = None
    structured_sections: tuple[str, ...] = ()
    cited_digest_ids: tuple[str, ...] = ()
    model_label: str | None = None
    limitations: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        result_id = _normalize_id(self.result_id, field="result_id")
        assert_language_model_status(self.status)
        if not self.provenance:
            msg = "missing provenance: LanguageModelResult requires provenance"
            raise CopilotError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        narrative_text = (
            None
            if self.narrative_text is None
            else self.narrative_text.strip() or None
        )
        structured_sections = tuple(
            s.strip() for s in self.structured_sections if s.strip()
        )
        cited_digest_ids = tuple(
            _normalize_id(d, field="cited_digest_ids") for d in self.cited_digest_ids
        )
        model_label = (
            None if self.model_label is None else self.model_label.strip() or None
        )
        limitations = tuple(n.strip() for n in self.limitations if n.strip())
        notes = tuple(n.strip() for n in self.notes if n.strip())
        if (
            self.status is LanguageModelStatus.COMPLETE
            and narrative_text is None
            and not structured_sections
        ):
            msg = (
                "LanguageModelResult COMPLETE requires narrative_text "
                "or structured_sections"
            )
            raise CopilotError(msg)
        object.__setattr__(self, "result_id", result_id)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "narrative_text", narrative_text)
        object.__setattr__(self, "structured_sections", structured_sections)
        object.__setattr__(self, "cited_digest_ids", cited_digest_ids)
        object.__setattr__(self, "model_label", model_label)
        object.__setattr__(self, "limitations", limitations)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class CopilotResponse:
    """Canonical immutable Copilot presentation / chat response snapshot."""

    copilot_id: str
    summary: CopilotSummary
    metadata: CopilotMetadata
    as_of: str
    status: ResponseStatus
    knowledge_graph_ref: KnowledgeGraphReference
    session_id: str | None = None
    intent: UserIntent | None = None
    context_bundle: ContextBundle | None = None
    explanation: Explanation | None = None
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
        copilot_id = _normalize_id(self.copilot_id, field="copilot_id")
        as_of = _non_empty(self.as_of, field="as_of")
        assert_response_status(self.status)
        if self.knowledge_graph_ref is None:
            msg = "broken references: KnowledgeGraphReference required"
            raise CopilotError(msg)
        session_id = (
            None
            if self.session_id is None
            else _normalize_id(self.session_id, field="session_id")
        )
        if self.context_bundle is not None:
            if (
                self.context_bundle.knowledge_graph_ref.id
                != self.knowledge_graph_ref.id
            ):
                msg = (
                    "broken references: ContextBundle KnowledgeGraphReference "
                    "does not match CopilotResponse"
                )
                raise CopilotError(msg)
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
            knowledge_graph_refs=(self.knowledge_graph_ref,),
        )
        limitations = tuple(n.strip() for n in self.limitations if n.strip())
        object.__setattr__(self, "copilot_id", copilot_id)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "session_id", session_id)
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
class CopilotProfile:
    """Aggregate root — cites upstream reports; owns conversation artifacts only."""

    identity: CopilotIdentity
    metadata: CopilotMetadata
    knowledge_graph_ref: KnowledgeGraphReference
    session: ConversationSession | None = None
    context: ConversationContext | None = None
    intents: tuple[UserIntent, ...] = ()
    context_bundles: tuple[ContextBundle, ...] = ()
    explanations: tuple[Explanation, ...] = ()
    summary: CopilotSummary | None = None
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
            msg = "missing identity: CopilotIdentity is required"
            raise CopilotError(msg)
        if self.knowledge_graph_ref is None:
            msg = "broken references: KnowledgeGraphReference required"
            raise CopilotError(msg)
        intents = _unique_intents(self.intents)
        bundles = _unique_bundles(self.context_bundles)
        explanations = _unique_explanations(self.explanations)
        for bundle in bundles:
            if bundle.knowledge_graph_ref.id != self.knowledge_graph_ref.id:
                msg = (
                    f"broken references: ContextBundle {bundle.bundle_id!r} "
                    "KnowledgeGraphReference mismatch"
                )
                raise CopilotError(msg)
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
            knowledge_graph_refs=(self.knowledge_graph_ref,),
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "intents", intents)
        object.__setattr__(self, "context_bundles", bundles)
        object.__setattr__(self, "explanations", explanations)
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
    def copilot_id(self) -> str:
        return self.identity.copilot_id


def _unique_turns(items: tuple[ConversationTurn, ...]) -> tuple[ConversationTurn, ...]:
    assert_unique_turn_ids(tuple(t.turn_id for t in items))
    sequences = [t.sequence for t in items]
    if len(sequences) != len(set(sequences)):
        msg = "duplicate turn ids: duplicate sequence numbers in session"
        raise CopilotError(msg)
    return tuple(items)


def _unique_intents(items: tuple[UserIntent, ...]) -> tuple[UserIntent, ...]:
    seen: set[str] = set()
    for item in items:
        if item.intent_id in seen:
            msg = f"duplicate intent ids: {item.intent_id!r}"
            raise CopilotError(msg)
        seen.add(item.intent_id)
    return tuple(items)


def _unique_bundles(items: tuple[ContextBundle, ...]) -> tuple[ContextBundle, ...]:
    seen: set[str] = set()
    for item in items:
        if item.bundle_id in seen:
            msg = f"duplicate context bundle ids: {item.bundle_id!r}"
            raise CopilotError(msg)
        seen.add(item.bundle_id)
    return tuple(items)


def _unique_explanations(items: tuple[Explanation, ...]) -> tuple[Explanation, ...]:
    seen: set[str] = set()
    for item in items:
        if item.explanation_id in seen:
            msg = f"duplicate explanation ids: {item.explanation_id!r}"
            raise CopilotError(msg)
        seen.add(item.explanation_id)
    return tuple(items)


def _reject_duplicate_report_refs(**groups: tuple[Any, ...]) -> None:
    for name, items in groups.items():
        seen_ids: set[str] = set()
        seen_reports: set[str] = set()
        for ref in items:
            if ref.id in seen_ids:
                msg = f"duplicate report references: {name} id {ref.id!r}"
                raise CopilotError(msg)
            if ref.report_id in seen_reports:
                msg = (
                    f"duplicate report references: {name} report_id "
                    f"{ref.report_id!r}"
                )
                raise CopilotError(msg)
            seen_ids.add(ref.id)
            seen_reports.add(ref.report_id)
