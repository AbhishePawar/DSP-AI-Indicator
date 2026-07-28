"""Contract tests — every adapter must satisfy the same port behaviours (PEP-002)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from production_platform import (
    FallbackCachePort,
    InMemoryBackgroundTaskPort,
    InMemoryCachePort,
    InMemoryDatabasePort,
    InMemoryJobQueuePort,
    InMemoryLockPort,
    InMemoryRateLimitPort,
    InMemorySessionPort,
    InMemoryStoragePort,
    LocalFilesystemStoragePort,
    Migration,
    MigrationRunner,
    PatternCacheInvalidation,
    ProviderError,
    RetryPolicy,
    StaticIndiaMarketCalendar,
)


class TestCacheContract:
    @pytest.fixture(params=["memory", "fallback"])
    def cache(self, request: pytest.FixtureRequest):
        if request.param == "memory":
            return InMemoryCachePort()
        primary = InMemoryCachePort()
        return FallbackCachePort(primary, InMemoryCachePort())

    def test_set_get_delete(self, cache) -> None:
        cache.set("a", {"n": 1}, ttl_seconds=60)
        assert cache.get("a") == {"n": 1}
        cache.delete("a")
        assert cache.get("a") is None

    def test_missing_key(self, cache) -> None:
        assert cache.get("missing") is None

    def test_invalidation_pattern(self) -> None:
        cache = InMemoryCachePort()
        cache.set("analyse:a", 1)
        cache.set("analyse:b", 2)
        cache.set("other", 3)
        inv = PatternCacheInvalidation(cache)
        assert inv.invalidate_pattern("analyse:*") == 2
        assert cache.get("other") == 3


class TestRateLimitContract:
    def test_allows_then_blocks(self) -> None:
        rl = InMemoryRateLimitPort()
        assert rl.allow("ip", limit=2, window_seconds=60) is True
        assert rl.allow("ip", limit=2, window_seconds=60) is True
        assert rl.allow("ip", limit=2, window_seconds=60) is False


class TestLockContract:
    def test_acquire_release(self) -> None:
        locks = InMemoryLockPort()
        assert locks.acquire("job", ttl_seconds=30) is True
        assert locks.acquire("job", ttl_seconds=30) is False
        locks.release("job")
        assert locks.acquire("job", ttl_seconds=30) is True


class TestSessionContract:
    def test_session_roundtrip(self) -> None:
        sessions = InMemorySessionPort()
        sessions.set("s1", {"user": "a"}, ttl_seconds=60)
        assert sessions.get("s1") == {"user": "a"}
        sessions.delete("s1")
        assert sessions.get("s1") is None


class TestStorageContract:
    @pytest.fixture(params=["memory", "local"])
    def storage(self, request: pytest.FixtureRequest, tmp_path: Path):
        if request.param == "memory":
            return InMemoryStoragePort()
        return LocalFilesystemStoragePort(tmp_path)

    def test_put_get_delete(self, storage) -> None:
        storage.put("f/a.txt", b"hello", content_type="text/plain")
        assert storage.get("f/a.txt") == b"hello"
        storage.delete("f/a.txt")
        assert storage.get("f/a.txt") is None


class TestDatabaseContract:
    def test_ping_and_migration(self) -> None:
        db = InMemoryDatabasePort()
        assert db.ping() is True
        runner = MigrationRunner(db)
        applied = runner.apply(
            [
                Migration(
                    version="001",
                    description="seed",
                    up_sql="CREATE TABLE IF NOT EXISTS audit (id TEXT)",
                ),
                Migration(
                    version="002",
                    description="row",
                    up_sql="INSERT INTO audit (id) VALUES ('a')",
                ),
            ]
        )
        assert applied == ("001", "002")
        assert runner.applied_versions() == ("001", "002")
        rows = db.fetchall("SELECT id FROM audit")
        assert rows == [{"id": "a"}]

    def test_transaction_rollback(self) -> None:
        db = InMemoryDatabasePort()
        db.execute("CREATE TABLE IF NOT EXISTS t (v TEXT)")
        try:
            with db.transaction() as txn:
                txn.execute("INSERT INTO t (v) VALUES ('x')")
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert db.fetchall("SELECT v FROM t") == []


class TestJobQueueContract:
    def test_enqueue_ack(self) -> None:
        q = InMemoryJobQueuePort()
        jid = q.enqueue("export", {"id": 1}, max_attempts=2)
        job = q.dequeue()
        assert job is not None
        assert job["job_id"] == jid
        q.ack(jid)
        assert q.dequeue() is None

    def test_retry_then_dead(self) -> None:
        q = InMemoryJobQueuePort(
            retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0.0)
        )
        jid = q.enqueue("failing", {}, max_attempts=2)
        job = q.dequeue()
        assert job is not None
        q.fail(jid, error="e1", retry=True)
        job2 = q.dequeue()
        assert job2 is not None
        q.fail(jid, error="e2", retry=True)
        assert len(q.list_dead_letters()) == 1


class TestBackgroundTaskContract:
    def test_submit_status(self) -> None:
        tasks = InMemoryBackgroundTaskPort()
        tid = tasks.submit("pdf", {"n": 1})
        assert tasks.status(tid) == "queued"


class TestIndiaCalendarContract:
    def test_weekend_and_holiday(self) -> None:
        cal = StaticIndiaMarketCalendar()
        assert cal.is_trading_day(date(2026, 1, 26)) is False  # Republic Day seed
        assert cal.is_trading_day(date(2026, 1, 24)) is False  # Saturday
        nxt = cal.next_trading_day(date(2026, 1, 26))
        assert cal.is_trading_day(nxt) is True


class TestFallbackCacheContract:
    def test_degrades_on_provider_error(self) -> None:
        class Boom:
            def get(self, key: str):
                raise ProviderError("down")

            def set(self, key: str, value, *, ttl_seconds=None):
                raise ProviderError("down")

            def delete(self, key: str):
                raise ProviderError("down")

        fb = FallbackCachePort(Boom(), InMemoryCachePort())  # type: ignore[arg-type]
        fb.set("k", 1)
        assert fb.using_fallback is True
        assert fb.get("k") == 1
