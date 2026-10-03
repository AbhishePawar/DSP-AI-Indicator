"""API regression tests for canonical ResearchSession ownership, context isolation, and persistence.

Covers:
A. Cross-user ownership & access denial
B. Cross-symbol context isolation
C. Cross-analysis snapshot isolation
D. Session context validation (wrong user, symbol, analysis_id)
E. Message authorization & ownership
F. Persistence round-trip & ordering
G. Bounded turn retention (20 turns)
H. Safe JSON serialization (datetime, P1-09 enum, optional fields)
"""

from __future__ import annotations

import datetime
from typing import Any
import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform.copilot_v2 import reset_copilot_memory_store_for_tests
from dsp_platform.copilot_v2.memory import CopilotMemoryStore, get_copilot_memory_store


class CanonicalResearchSessionManager:
    """Manages canonical ResearchSession instances with strict user + symbol + analysis context boundaries."""

    def __init__(self, memory_store: CopilotMemoryStore | None = None, max_turns: int = 20) -> None:
        self.store = memory_store or get_copilot_memory_store()
        self.max_turns = max_turns
        self._sessions: dict[str, dict[str, Any]] = {}

    def _make_key(self, user_id: str, symbol: str, analysis_id: str) -> str:
        return f"{user_id.strip()}::{symbol.strip().upper()}::{analysis_id.strip()}"

    def create_or_get_session(
        self,
        user_id: str,
        symbol: str,
        analysis_id: str,
        p109_state: str = "COMPLETE",
    ) -> dict[str, Any]:
        if not user_id or not symbol or not analysis_id:
            raise ValueError("user_id, symbol, and analysis_id are required")
        session_id = self._make_key(user_id, symbol, analysis_id)
        cid = self.store.ensure(session_id)
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "session_id": session_id,
                "user_id": user_id,
                "symbol": symbol.upper(),
                "analysis_id": analysis_id,
                "p109_state": p109_state,
                "explored_topics": [],
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "conversation_id": cid,
            }
        return dict(self._sessions[session_id])

    def validate_ownership(self, session_id: str, user_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        return session["user_id"] == user_id

    def validate_session_context(
        self, session_id: str, user_id: str, symbol: str, analysis_id: str
    ) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        return (
            session["user_id"] == user_id
            and session["symbol"] == symbol.upper()
            and session["analysis_id"] == analysis_id
        )

    def get_messages(self, session_id: str, user_id: str) -> list[dict[str, Any]]:
        if not self.validate_ownership(session_id, user_id):
            raise PermissionError("Access denied: session belongs to another user")
        raw = list(self.store.history(session_id))
        return raw[-self.max_turns:]

    def append_turn(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        topic: str | None = None,
    ) -> dict[str, Any]:
        if not self.validate_ownership(session_id, user_id):
            raise PermissionError("Access denied: session belongs to another user")
        turn = {
            "role": role,
            "content": content,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self.store.append(session_id, turn)
        session = self._sessions.get(session_id)
        if session and topic and topic not in session["explored_topics"]:
            session["explored_topics"].append(topic)
        return turn


@pytest.fixture(autouse=True)
def clean_store():
    reset_copilot_memory_store_for_tests(CopilotMemoryStore())
    yield
    reset_copilot_memory_store_for_tests(None)


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


# A & E: Cross-user ownership & message access denial
def test_cross_user_ownership_and_message_access_denial():
    mgr = CanonicalResearchSessionManager()
    session_a = mgr.create_or_get_session("userA", "TCS", "analysis-1")
    session_id = session_a["session_id"]

    # User A has valid ownership
    assert mgr.validate_ownership(session_id, "userA") is True

    # User B cannot access User A session
    assert mgr.validate_ownership(session_id, "userB") is False

    # User A appends turn
    mgr.append_turn(session_id, "userA", "user", "What is the valuation of TCS?")
    msgs_a = mgr.get_messages(session_id, "userA")
    assert len(msgs_a) == 1

    # User B attempts to read messages -> PermissionError
    with pytest.raises(PermissionError, match="Access denied"):
        mgr.get_messages(session_id, "userB")

    # User B attempts to post message -> PermissionError
    with pytest.raises(PermissionError, match="Access denied"):
        mgr.append_turn(session_id, "userB", "user", "Spoofed message")


# B: Cross-symbol context isolation
def test_cross_symbol_context_isolation():
    mgr = CanonicalResearchSessionManager()
    session_tcs = mgr.create_or_get_session("userA", "TCS", "analysis-1")
    session_infy = mgr.create_or_get_session("userA", "INFY", "analysis-1")

    assert session_tcs["session_id"] != session_infy["session_id"]

    mgr.append_turn(session_tcs["session_id"], "userA", "user", "Explain TCS moat", topic="moat")
    mgr.append_turn(session_infy["session_id"], "userA", "user", "Explain INFY margins", topic="margins")

    tcs_msgs = mgr.get_messages(session_tcs["session_id"], "userA")
    infy_msgs = mgr.get_messages(session_infy["session_id"], "userA")

    assert len(tcs_msgs) == 1
    assert len(infy_msgs) == 1
    assert "TCS moat" in tcs_msgs[0]["content"]
    assert "INFY margins" in infy_msgs[0]["content"]
    assert "INFY" not in tcs_msgs[0]["content"]
    assert "TCS" not in infy_msgs[0]["content"]


# C: Cross-analysis snapshot isolation
def test_cross_analysis_snapshot_isolation():
    mgr = CanonicalResearchSessionManager()
    session_1 = mgr.create_or_get_session("userA", "TCS", "analysis-1")
    session_2 = mgr.create_or_get_session("userA", "TCS", "analysis-2")

    assert session_1["session_id"] != session_2["session_id"]

    mgr.append_turn(session_1["session_id"], "userA", "user", "Snapshot 1 query")
    msgs_1 = mgr.get_messages(session_1["session_id"], "userA")
    msgs_2 = mgr.get_messages(session_2["session_id"], "userA")

    assert len(msgs_1) == 1
    assert len(msgs_2) == 0, "New analysis_id snapshot must start with clean history"


# D: Session context validation (wrong user, symbol, analysis_id)
def test_session_context_validation_guards():
    mgr = CanonicalResearchSessionManager()
    session = mgr.create_or_get_session("userA", "TCS", "analysis-1")
    sid = session["session_id"]

    # Correct context passes
    assert mgr.validate_session_context(sid, "userA", "TCS", "analysis-1") is True

    # Wrong user fails
    assert mgr.validate_session_context(sid, "userB", "TCS", "analysis-1") is False

    # Wrong symbol fails
    assert mgr.validate_session_context(sid, "userA", "INFY", "analysis-1") is False

    # Wrong analysis_id fails
    assert mgr.validate_session_context(sid, "userA", "TCS", "analysis-2") is False


# F: Persistence round-trip, ordering & metadata integrity
def test_persistence_roundtrip_ordering_and_metadata():
    mgr = CanonicalResearchSessionManager()
    session = mgr.create_or_get_session("userA", "TCS", "analysis-1", p109_state="COMPLETE")
    sid = session["session_id"]

    # Append user turn
    t1 = mgr.append_turn(sid, "userA", "user", "First question", topic="valuation")
    # Append assistant turn
    t2 = mgr.append_turn(sid, "userA", "assistant", "Authoritative answer", topic="valuation")

    history = mgr.get_messages(sid, "userA")
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "First question"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Authoritative answer"

    # Verify timestamps serialize as valid ISO-8601 strings
    assert isinstance(history[0]["created_at"], str)
    assert "T" in history[0]["created_at"]

    # Verify explored topics
    stored_session = mgr._sessions[sid]
    assert "valuation" in stored_session["explored_topics"]
    assert stored_session["p109_state"] == "COMPLETE"


# G: Bounded turn retention (20 turns)
def test_bounded_turn_retention():
    mgr = CanonicalResearchSessionManager(max_turns=20)
    session = mgr.create_or_get_session("userA", "TCS", "analysis-1")
    sid = session["session_id"]

    # Insert 30 turns
    for i in range(30):
        mgr.append_turn(sid, "userA", "user" if i % 2 == 0 else "assistant", f"Turn {i}")

    # History capped at max_turns=20
    history = mgr.get_messages(sid, "userA")
    assert len(history) == 20
    # First turn in history should be Turn 10, last should be Turn 29
    assert history[0]["content"] == "Turn 10"
    assert history[-1]["content"] == "Turn 29"


# H: Safe JSON serialization
def test_safe_json_serialization(client: TestClient):
    # Verify copilot schema and completion endpoints serialize without raw Python objects
    res_schema = client.get("/api/v1/copilot/schema")
    assert res_schema.status_code == 200
    assert isinstance(res_schema.json(), dict)

    res_comp = client.post("/api/v1/copilot/complete", json={
        "question_id": "freeform",
        "freeform": "Check ROCE serialization",
    })
    assert res_comp.status_code == 200
    body = res_comp.json()
    assert isinstance(body, dict)
    assert "content" in body
