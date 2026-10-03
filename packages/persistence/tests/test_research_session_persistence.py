"""Unit and in-memory persistence tests for ResearchSessionService (EPIC-A008)."""

from __future__ import annotations

import concurrent.futures
import pytest

from persistence import (
    InMemoryStorageProvider,
    ResearchSessionService,
    ValidationError,
    NotFoundError,
    compute_session_id,
    DEFAULT_MAX_TURNS,
)


@pytest.fixture
def storage() -> InMemoryStorageProvider:
    return InMemoryStorageProvider()


@pytest.fixture
def service(storage: InMemoryStorageProvider) -> ResearchSessionService:
    return ResearchSessionService(storage)


def test_session_creation_and_retrieval(service: ResearchSessionService) -> None:
    session = service.get_or_create_session(
        user_id="user-100",
        symbol="AAPL",
        analysis_id="an-2026-001",
        metadata={"client": "web"},
    )
    assert session["user_id"] == "user-100"
    assert session["symbol"] == "AAPL"
    assert session["analysis_id"] == "an-2026-001"
    assert session["turn_count"] == 0
    assert session["turn_ids"] == []
    assert session["metadata"] == {"client": "web"}

    sid = session["session_id"]
    expected_sid = compute_session_id("user-100", "AAPL", "an-2026-001")
    assert sid == expected_sid

    # Same parameters return existing session without mutation
    same_session = service.get_or_create_session(
        user_id="user-100",
        symbol="AAPL",
        analysis_id="an-2026-001",
    )
    assert same_session["session_id"] == sid
    assert same_session["metadata"] == {"client": "web"}

    # Direct retrieval
    fetched = service.get_session(sid, user_id="user-100")
    assert fetched["session_id"] == sid


def test_ownership_isolation(service: ResearchSessionService) -> None:
    session = service.get_or_create_session(
        user_id="user-alice",
        symbol="MSFT",
        analysis_id="an-msft-01",
    )
    sid = session["session_id"]

    # Different user cannot read session
    with pytest.raises(ValidationError, match="ownership mismatch"):
        service.get_session(sid, user_id="user-bob")

    # Different user cannot append turn
    with pytest.raises(ValidationError, match="unauthorized user"):
        service.append_turn(
            session_id=sid,
            user_id="user-bob",
            role="user",
            content="Hello from Bob",
        )

    # Different user cannot read turns
    with pytest.raises(ValidationError, match="ownership mismatch"):
        service.get_turns(sid, user_id="user-bob")


def test_context_validation(service: ResearchSessionService) -> None:
    session = service.get_or_create_session(
        user_id="user-carol",
        symbol="NVDA",
        analysis_id="an-nvda-01",
    )
    sid = session["session_id"]

    # Context symbol mismatch
    with pytest.raises(ValidationError, match="symbol mismatch"):
        service.append_turn(
            session_id=sid,
            user_id="user-carol",
            role="user",
            content="Explain moat",
            symbol="TSLA",
            analysis_id="an-nvda-01",
        )

    # Context analysis_id mismatch
    with pytest.raises(ValidationError, match="analysis_id mismatch"):
        service.append_turn(
            session_id=sid,
            user_id="user-carol",
            role="user",
            content="Explain moat",
            symbol="NVDA",
            analysis_id="an-wrong-id",
        )


def test_first_turn_append_and_synchronization(service: ResearchSessionService) -> None:
    session = service.get_or_create_session(
        user_id="user-dan",
        symbol="GOOGL",
        analysis_id="an-googl-01",
    )
    sid = session["session_id"]

    turn, updated_session = service.append_turn(
        session_id=sid,
        user_id="user-dan",
        role="user",
        content="What is the operating margin trend?",
        symbol="GOOGL",
        analysis_id="an-googl-01",
        metadata={"topic": "margins"},
    )

    assert turn["session_id"] == sid
    assert turn["role"] == "user"
    assert turn["content"] == "What is the operating margin trend?"
    assert turn["metadata"] == {"topic": "margins"}

    assert updated_session["turn_count"] == 1
    assert len(updated_session["turn_ids"]) == 1
    assert updated_session["turn_ids"][0] == turn["turn_id"]

    # Retrieve turns
    turns = service.get_turns(sid, user_id="user-dan")
    assert len(turns) == 1
    assert turns[0]["turn_id"] == turn["turn_id"]


def test_chronological_ordering(service: ResearchSessionService) -> None:
    session = service.get_or_create_session(
        user_id="user-eve",
        symbol="AMZN",
        analysis_id="an-amzn-01",
    )
    sid = session["session_id"]

    turn1, _ = service.append_turn(
        session_id=sid,
        user_id="user-eve",
        role="user",
        content="Turn 1",
    )
    turn2, _ = service.append_turn(
        session_id=sid,
        user_id="user-eve",
        role="assistant",
        content="Turn 2",
    )
    turn3, _ = service.append_turn(
        session_id=sid,
        user_id="user-eve",
        role="user",
        content="Turn 3",
    )

    turns = service.get_turns(sid, user_id="user-eve")
    assert len(turns) == 3
    assert [t["turn_id"] for t in turns] == [turn1["turn_id"], turn2["turn_id"], turn3["turn_id"]]


def test_twenty_turn_fifo_retention(service: ResearchSessionService) -> None:
    session = service.get_or_create_session(
        user_id="user-frank",
        symbol="META",
        analysis_id="an-meta-01",
    )
    sid = session["session_id"]

    # Append 25 turns
    created_turns = []
    for i in range(25):
        role = "user" if i % 2 == 0 else "assistant"
        turn, s = service.append_turn(
            session_id=sid,
            user_id="user-frank",
            role=role,
            content=f"Turn number {i}",
            metadata={"idx": i},
        )
        created_turns.append(turn)

    # Check updated session turn_count is capped at 20
    final_session = service.get_session(sid, user_id="user-frank")
    assert final_session["turn_count"] == DEFAULT_MAX_TURNS
    assert len(final_session["turn_ids"]) == DEFAULT_MAX_TURNS

    # Retrieved turns must be exactly the last 20 (indices 5 to 24)
    retained_turns = service.get_turns(sid, user_id="user-frank")
    assert len(retained_turns) == 20
    for idx, t in enumerate(retained_turns):
        expected_i = idx + 5
        assert t["content"] == f"Turn number {expected_i}"
        assert t["metadata"]["idx"] == expected_i

    # Oldest 5 turns must have been evicted from storage
    for evicted in created_turns[:5]:
        assert service.storage.get("research_turns", evicted["turn_id"]) is None


def test_concurrent_first_append_safety(service: ResearchSessionService) -> None:
    session = service.get_or_create_session(
        user_id="user-grace",
        symbol="TSM",
        analysis_id="an-tsm-01",
    )
    sid = session["session_id"]

    # 10 threads trying to append the first turns concurrently
    def _do_append(thread_idx: int):
        return service.append_turn(
            session_id=sid,
            user_id="user-grace",
            role="user",
            content=f"Concurrent first turn {thread_idx}",
            symbol="TSM",
            analysis_id="an-tsm-01",
            metadata={"thread": thread_idx},
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_do_append, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 10

    # Session turn count must accurately reflect 10 turns
    final_session = service.get_session(sid, user_id="user-grace")
    assert final_session["turn_count"] == 10
    assert len(final_session["turn_ids"]) == 10

    turns = service.get_turns(sid, user_id="user-grace")
    assert len(turns) == 10


def test_concurrent_appends_fifo_preservation(service: ResearchSessionService) -> None:
    session = service.get_or_create_session(
        user_id="user-heidi",
        symbol="BRK",
        analysis_id="an-brk-01",
    )
    sid = session["session_id"]

    # 30 concurrent appends
    def _append_worker(idx: int):
        return service.append_turn(
            session_id=sid,
            user_id="user-heidi",
            role="user",
            content=f"Threaded turn {idx}",
            metadata={"seq": idx},
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(_append_worker, i) for i in range(30)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 30

    final_session = service.get_session(sid, user_id="user-heidi")
    assert final_session["turn_count"] == 20
    assert len(final_session["turn_ids"]) == 20

    turns = service.get_turns(sid, user_id="user-heidi")
    assert len(turns) == 20
