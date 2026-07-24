"""AI Copilot validation helpers — contracts only (J1.0).

No conversation orchestration, explanation generation, LLM invocation,
or persistence.
"""

from __future__ import annotations

from core.exceptions import ValidationError

from copilot.enums import (
    ConversationRole,
    ConversationState,
    ConversationStatus,
    ExplanationType,
    LanguageModelStatus,
    ResponseStatus,
    UserIntentType,
)
from copilot.exceptions import CopilotError

__all__ = [
    "ALLOWED_CONVERSATION_TRANSITIONS",
    "CONVERSATION_ROLES",
    "CONVERSATION_STATES",
    "CONVERSATION_STATUSES",
    "EXPLANATION_TYPES",
    "LANGUAGE_MODEL_STATUSES",
    "RESPONSE_STATUSES",
    "USER_INTENT_TYPES",
    "assert_conversation_role",
    "assert_conversation_state",
    "assert_conversation_status",
    "assert_explanation_type",
    "assert_language_model_status",
    "assert_legal_conversation_transition",
    "assert_response_status",
    "assert_unique_copilot_ids",
    "assert_unique_session_ids",
    "assert_unique_turn_ids",
    "assert_user_intent_type",
]

CONVERSATION_STATES: frozenset[ConversationState] = frozenset(ConversationState)
CONVERSATION_STATUSES: frozenset[ConversationStatus] = frozenset(ConversationStatus)
CONVERSATION_ROLES: frozenset[ConversationRole] = frozenset(ConversationRole)
USER_INTENT_TYPES: frozenset[UserIntentType] = frozenset(UserIntentType)
EXPLANATION_TYPES: frozenset[ExplanationType] = frozenset(ExplanationType)
RESPONSE_STATUSES: frozenset[ResponseStatus] = frozenset(ResponseStatus)
LANGUAGE_MODEL_STATUSES: frozenset[LanguageModelStatus] = frozenset(
    LanguageModelStatus
)

ALLOWED_CONVERSATION_TRANSITIONS: dict[
    ConversationState, frozenset[ConversationState]
] = {
    ConversationState.PENDING: frozenset(
        {
            ConversationState.ACTIVE,
            ConversationState.CLARIFYING,
            ConversationState.CANCELLED,
            ConversationState.FAILED,
        }
    ),
    ConversationState.ACTIVE: frozenset(
        {
            ConversationState.ACTIVE,
            ConversationState.CLARIFYING,
            ConversationState.COMPLETED,
            ConversationState.FAILED,
            ConversationState.CANCELLED,
        }
    ),
    ConversationState.CLARIFYING: frozenset(
        {
            ConversationState.ACTIVE,
            ConversationState.CLARIFYING,
            ConversationState.COMPLETED,
            ConversationState.FAILED,
            ConversationState.CANCELLED,
        }
    ),
    ConversationState.COMPLETED: frozenset(),
    ConversationState.FAILED: frozenset(),
    ConversationState.CANCELLED: frozenset(),
}


def assert_conversation_state(state: ConversationState) -> None:
    if state not in CONVERSATION_STATES:
        msg = f"illegal conversation states: {state!r}"
        raise CopilotError(msg)


def assert_conversation_status(status: ConversationStatus) -> None:
    if status not in CONVERSATION_STATUSES:
        msg = f"illegal conversation statuses: {status!r}"
        raise CopilotError(msg)


def assert_legal_conversation_transition(
    source: ConversationState, target: ConversationState
) -> None:
    """Reject illegal ConversationState transitions."""
    assert_conversation_state(source)
    assert_conversation_state(target)
    allowed = ALLOWED_CONVERSATION_TRANSITIONS.get(source, frozenset())
    if target not in allowed:
        msg = (
            f"illegal conversation transitions: {source.value!r} -> {target.value!r}"
        )
        raise CopilotError(msg)


def assert_conversation_role(role: ConversationRole) -> None:
    if role not in CONVERSATION_ROLES:
        msg = f"illegal conversation roles: {role!r}"
        raise CopilotError(msg)


def assert_user_intent_type(intent_type: UserIntentType) -> None:
    if intent_type not in USER_INTENT_TYPES:
        msg = f"illegal intent types: {intent_type!r}"
        raise CopilotError(msg)


def assert_explanation_type(explanation_type: ExplanationType) -> None:
    if explanation_type not in EXPLANATION_TYPES:
        msg = f"illegal explanation types: {explanation_type!r}"
        raise CopilotError(msg)


def assert_response_status(status: ResponseStatus) -> None:
    if status not in RESPONSE_STATUSES:
        msg = f"illegal response statuses: {status!r}"
        raise CopilotError(msg)


def assert_language_model_status(status: LanguageModelStatus) -> None:
    if status not in LANGUAGE_MODEL_STATUSES:
        msg = f"illegal language model statuses: {status!r}"
        raise CopilotError(msg)


def assert_unique_turn_ids(turn_ids: tuple[str, ...]) -> None:
    seen: set[str] = set()
    for raw in turn_ids:
        cleaned = raw.strip().lower()
        if not cleaned:
            msg = "turn_id must not be empty"
            raise ValidationError(msg)
        if cleaned in seen:
            msg = f"duplicate turn ids: {cleaned!r}"
            raise CopilotError(msg)
        seen.add(cleaned)


def assert_unique_session_ids(session_ids: tuple[str, ...]) -> None:
    seen: set[str] = set()
    for raw in session_ids:
        cleaned = raw.strip().lower()
        if not cleaned:
            msg = "session_id must not be empty"
            raise ValidationError(msg)
        if cleaned in seen:
            msg = f"duplicate session ids: {cleaned!r}"
            raise CopilotError(msg)
        seen.add(cleaned)


def assert_unique_copilot_ids(copilot_ids: tuple[str, ...]) -> None:
    seen: set[str] = set()
    for raw in copilot_ids:
        cleaned = raw.strip().lower()
        if not cleaned:
            msg = "copilot_id must not be empty"
            raise ValidationError(msg)
        if cleaned in seen:
            msg = f"duplicate copilot ids: {cleaned!r}"
            raise CopilotError(msg)
        seen.add(cleaned)
