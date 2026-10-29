"""Research Session Persistence Service (EPIC-A008).

Stores session metadata, context references, and conversation turns.
Never duplicates raw financial research payloads or valuation models.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from persistence.exceptions import NotFoundError, ValidationError
from persistence.interfaces import StorageProviderPort
from persistence.serde import to_plain_jsonable

__all__ = [
    "COLLECTION_RESEARCH_SESSIONS",
    "COLLECTION_RESEARCH_TURNS",
    "DEFAULT_MAX_TURNS",
    "ResearchSessionService",
    "compute_session_id",
    "get_research_session_service",
    "reset_research_session_service_for_tests",
]

COLLECTION_RESEARCH_SESSIONS = "research_sessions"
COLLECTION_RESEARCH_TURNS = "research_turns"
DEFAULT_MAX_TURNS = 20


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def compute_session_id(user_id: str, symbol: str, analysis_id: str) -> str:
    """Deterministic session identity based on authenticated user + symbol + analysis_id."""
    clean_user = str(user_id or "").strip()
    clean_symbol = str(symbol or "").strip().upper()
    clean_analysis = str(analysis_id or "").strip()
    if not clean_user:
        raise ValidationError("user_id is required")
    if not clean_symbol:
        raise ValidationError("symbol is required")
    if not clean_analysis:
        raise ValidationError("analysis_id is required")

    composite = f"{clean_user}:{clean_symbol}:{clean_analysis}"
    digest = hashlib.sha256(composite.encode("utf-8")).hexdigest()[:24]
    return f"rs_{clean_symbol.lower()}_{digest}"


class ResearchSessionService:
    """Service managing durable research session persistence and turn streaming."""

    def __init__(self, storage: StorageProviderPort, *, max_turns: int = DEFAULT_MAX_TURNS) -> None:
        self._storage = storage
        self._max_turns = max_turns

    @property
    def storage(self) -> StorageProviderPort:
        return self._storage

    def get_or_create_session(
        self,
        *,
        user_id: str,
        symbol: str,
        analysis_id: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Retrieve existing session or create deterministically if absent."""
        clean_user = str(user_id or "").strip()
        clean_symbol = str(symbol or "").strip().upper()
        clean_analysis = str(analysis_id or "").strip()
        session_id = compute_session_id(clean_user, clean_symbol, clean_analysis)

        now_iso = _utc_now_iso()
        init_payload = {
            "session_id": session_id,
            "user_id": clean_user,
            "symbol": clean_symbol,
            "analysis_id": clean_analysis,
            "turn_count": 0,
            "turn_ids": [],
            "created_at": now_iso,
            "updated_at": now_iso,
            "metadata": to_plain_jsonable(dict(metadata or {})),
        }

        stored = self._storage.atomic_put_if_absent(
            COLLECTION_RESEARCH_SESSIONS, session_id, init_payload
        )
        res = dict(stored)

        # Server-authoritative ownership check
        if str(res.get("user_id", "")) != clean_user:
            raise ValidationError("Access denied: session ownership mismatch")

        # Context validation
        if str(res.get("symbol", "")).upper() != clean_symbol:
            raise ValidationError("Context validation failed: symbol mismatch")
        if str(res.get("analysis_id", "")) != clean_analysis:
            raise ValidationError("Context validation failed: analysis_id mismatch")

        return res

    def get_session(
        self,
        session_id: str,
        *,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Fetch session by ID with ownership enforcement."""
        clean_sid = str(session_id or "").strip()
        if not clean_sid:
            raise ValidationError("session_id is required")

        row = self._storage.get(COLLECTION_RESEARCH_SESSIONS, clean_sid)
        if row is None:
            raise NotFoundError(f"Research session not found: {clean_sid}")

        session = dict(row)
        if user_id is not None:
            clean_uid = str(user_id).strip()
            if str(session.get("user_id", "")) != clean_uid:
                raise ValidationError("Access denied: session ownership mismatch")

        return session

    def get_turns(
        self,
        session_id: str,
        *,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return retained turns for a session in chronological order."""
        session = self.get_session(session_id, user_id=user_id)
        turn_ids = list(session.get("turn_ids") or [])

        turns: list[dict[str, Any]] = []
        for tid in turn_ids:
            turn_row = self._storage.get(COLLECTION_RESEARCH_TURNS, tid)
            if turn_row is not None:
                turns.append(dict(turn_row))

        # Ensure chronological ordering by created_at
        turns.sort(key=lambda t: str(t.get("created_at", "")))
        return turns

    def append_turn(
        self,
        *,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        symbol: str | None = None,
        analysis_id: str | None = None,
        turn_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Append turn atomically, enforcing FIFO 20-turn retention and ownership."""
        clean_sid = str(session_id or "").strip()
        clean_uid = str(user_id or "").strip()
        clean_role = str(role or "").strip().lower()

        if not clean_sid:
            raise ValidationError("session_id is required")
        if not clean_uid:
            raise ValidationError("user_id is required")
        if clean_role not in ("user", "assistant", "system"):
            raise ValidationError(f"Invalid role: {role}")
        if content is None:
            raise ValidationError("content is required")

        tid = str(turn_id or "").strip() or f"turn_{clean_sid}_{uuid4().hex[:12]}"
        now_iso = _utc_now_iso()

        turn_payload = {
            "turn_id": tid,
            "session_id": clean_sid,
            "user_id": clean_uid,
            "role": clean_role,
            "content": str(content),
            "created_at": now_iso,
            "updated_at": now_iso,
            "metadata": to_plain_jsonable(dict(metadata or {})),
        }

        turn_stored, session_stored = self._storage.append_research_turn_atomic(
            session_collection=COLLECTION_RESEARCH_SESSIONS,
            turns_collection=COLLECTION_RESEARCH_TURNS,
            session_id=clean_sid,
            turn_id=tid,
            turn_data=turn_payload,
            max_turns=self._max_turns,
            expected_user_id=clean_uid,
            expected_symbol=symbol,
            expected_analysis_id=analysis_id,
        )

        return dict(turn_stored), dict(session_stored)


_RESEARCH_SESSION_SERVICE: ResearchSessionService | None = None


def get_research_session_service() -> ResearchSessionService:
    global _RESEARCH_SESSION_SERVICE
    if _RESEARCH_SESSION_SERVICE is None:
        from persistence.registry import build_default_storage
        _RESEARCH_SESSION_SERVICE = ResearchSessionService(build_default_storage())
    return _RESEARCH_SESSION_SERVICE


def reset_research_session_service_for_tests(
    service: ResearchSessionService | None = None,
) -> None:
    global _RESEARCH_SESSION_SERVICE
    _RESEARCH_SESSION_SERVICE = service
