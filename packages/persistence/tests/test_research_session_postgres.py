"""PostgreSQL persistence integration tests for ResearchSessionService (EPIC-A008).

STRICTLY OPT-IN:
These tests ONLY run when BOTH:
  DSP_DATABASE_URL is set AND
  DSP_RUN_POSTGRES_TESTS=1

SAFETY GUARANTEES:
- Uses uniquely namespaced test IDs (never production or real analysis IDs)
- Cleans up only its own namespace in fixture teardown
- NEVER calls TRUNCATE
- NEVER calls DROP
- NEVER performs unscoped DELETE
"""

from __future__ import annotations

import concurrent.futures
import os
import uuid
import pytest

from persistence import (
    PostgresStorageProvider,
    ResearchSessionService,
    ValidationError,
    NotFoundError,
    DEFAULT_MAX_TURNS,
)

DATABASE_URL = os.environ.get("DSP_DATABASE_URL", "").strip()
RUN_POSTGRES_TESTS = os.environ.get("DSP_RUN_POSTGRES_TESTS", "").strip() == "1"

pytestmark = pytest.mark.skipif(
    not (DATABASE_URL and RUN_POSTGRES_TESTS),
    reason="PostgreSQL tests require BOTH DSP_DATABASE_URL and DSP_RUN_POSTGRES_TESTS=1",
)


@pytest.fixture
def pg_namespace():
    ns = f"test_pg_rs_{uuid.uuid4().hex[:10]}"
    yield ns

    # Scoped cleanup of only this namespace
    if DATABASE_URL and RUN_POSTGRES_TESTS:
        try:
            store = PostgresStorageProvider(DATABASE_URL)
            conn = store._connect()
            with conn.cursor() as cur:
                # Scoped delete ONLY for rows matching this test namespace
                cur.execute(
                    "DELETE FROM a008_entities WHERE collection IN ('research_sessions', 'research_turns') "
                    "AND (entity_id LIKE %s OR payload->>'analysis_id' LIKE %s)",
                    (f"%{ns}%", f"%{ns}%"),
                )
                conn.commit()
            conn.close()
        except Exception:
            pass


@pytest.fixture
def pg_service(pg_namespace) -> ResearchSessionService:
    store = PostgresStorageProvider(DATABASE_URL)
    return ResearchSessionService(store)


def test_postgres_session_lifecycle(pg_service: ResearchSessionService, pg_namespace: str) -> None:
    user_id = f"user_{pg_namespace}"
    symbol = "NVDA"
    analysis_id = f"an_{pg_namespace}"

    session = pg_service.get_or_create_session(
        user_id=user_id,
        symbol=symbol,
        analysis_id=analysis_id,
        metadata={"env": "test"},
    )
    sid = session["session_id"]
    assert session["user_id"] == user_id
    assert session["symbol"] == symbol
    assert session["analysis_id"] == analysis_id
    assert session["turn_count"] == 0

    # Retrieve from PostgreSQL
    fetched = pg_service.get_session(sid, user_id=user_id)
    assert fetched["session_id"] == sid
    assert fetched["metadata"] == {"env": "test"}


def test_postgres_append_and_fifo_eviction(pg_service: ResearchSessionService, pg_namespace: str) -> None:
    user_id = f"user_{pg_namespace}"
    symbol = "AAPL"
    analysis_id = f"an_{pg_namespace}"

    session = pg_service.get_or_create_session(
        user_id=user_id,
        symbol=symbol,
        analysis_id=analysis_id,
    )
    sid = session["session_id"]

    # Append 25 turns to test FIFO trim down to 20
    for i in range(25):
        pg_service.append_turn(
            session_id=sid,
            user_id=user_id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"Postgres turn {i}",
            metadata={"seq": i},
        )

    # Verify session reflects 20 turns
    final_session = pg_service.get_session(sid, user_id=user_id)
    assert final_session["turn_count"] == DEFAULT_MAX_TURNS
    assert len(final_session["turn_ids"]) == DEFAULT_MAX_TURNS

    # Verify retained turns are chronological indices 5..24
    turns = pg_service.get_turns(sid, user_id=user_id)
    assert len(turns) == 20
    for idx, t in enumerate(turns):
        expected_seq = idx + 5
        assert t["metadata"]["seq"] == expected_seq


def test_postgres_concurrent_appends(pg_service: ResearchSessionService, pg_namespace: str) -> None:
    user_id = f"user_{pg_namespace}"
    symbol = "MSFT"
    analysis_id = f"an_{pg_namespace}"

    session = pg_service.get_or_create_session(
        user_id=user_id,
        symbol=symbol,
        analysis_id=analysis_id,
    )
    sid = session["session_id"]

    def _worker(idx: int):
        svc = ResearchSessionService(PostgresStorageProvider(DATABASE_URL))
        return svc.append_turn(
            session_id=sid,
            user_id=user_id,
            role="user",
            content=f"Concurrent pg turn {idx}",
            metadata={"worker_idx": idx},
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_worker, i) for i in range(15)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 15

    final_session = pg_service.get_session(sid, user_id=user_id)
    assert final_session["turn_count"] == 15
    assert len(final_session["turn_ids"]) == 15

    turns = pg_service.get_turns(sid, user_id=user_id)
    assert len(turns) == 15
