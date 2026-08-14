"""Conversation context (EPIC-A001) — ephemeral Q&A history only."""

from __future__ import annotations

from threading import RLock
from typing import Any
from uuid import uuid4

__all__ = [
    "ConversationStore",
    "get_conversation_store",
    "reset_conversation_store_for_tests",
]


class ConversationStore:
    """In-memory conversation turns — never stores mutable research payloads."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._turns: dict[str, list[dict[str, Any]]] = {}

    def ensure(self, conversation_id: str | None) -> str:
        cid = conversation_id or str(uuid4())
        with self._lock:
            self._turns.setdefault(cid, [])
        return cid

    def append(self, conversation_id: str, turn: dict[str, Any]) -> None:
        with self._lock:
            self._turns.setdefault(conversation_id, []).append(dict(turn))

    def history(self, conversation_id: str) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(self._turns.get(conversation_id, []))


_STORE: ConversationStore | None = None


def get_conversation_store() -> ConversationStore:
    global _STORE
    if _STORE is None:
        _STORE = ConversationStore()
    return _STORE


def reset_conversation_store_for_tests(store: ConversationStore | None = None) -> None:
    global _STORE
    _STORE = store
