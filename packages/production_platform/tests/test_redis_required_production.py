"""Production Redis honesty — runtime dependency + adapter selection tests.

Validates that:
A. Production dependency/configuration: root pyproject.toml [api] declares redis>=5.0
   and Dockerfile verifies redis in builder and runtime stages.
B. Redis adapter: RedisCachePort can be constructed and behaves correctly.
C. Redis stack: try_build_redis_stack() returns real ports when Redis is available.
D. Required Redis behavior: When DSP_REDIS_FALLBACK=false and Redis cannot be
   initialized, production does not silently claim Redis is active.
E. Health: Health/readiness accurately reflects Redis state and reports Redis PASS
   when Redis-backed adapters are active.
F. Offline/development behavior: InMemoryCachePort remains valid for explicitly
   offline or development configurations.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from production_platform.adapters.redis_stack import (
    RedisCachePort,
    try_build_redis_stack,
)
from production_platform.production.cache import InMemoryCachePort
from production_platform.production.configuration import (
    ConfigurationManager,
    Environment,
    ProductionConfiguration,
    RedisSettings,
)
from production_platform.production.health import HealthManager, HealthStatus
from production_platform.production.infrastructure import (
    InfrastructureBundle,
    InfrastructureDiagnostics,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]


class TestProductionRedisDependency:
    """Root pyproject.toml and Dockerfile must guarantee redis client presence."""

    def test_root_api_extra_declares_redis(self) -> None:
        pyproject = tomllib.loads(
            (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        api_extra = pyproject["project"]["optional-dependencies"]["api"]
        assert any(dep.startswith("redis") for dep in api_extra), (
            "root [api] extra must include redis>=5.0 because the production "
            "Docker image installs pip install '.[api]'"
        )

    def test_backend_dockerfile_verifies_redis(self) -> None:
        dockerfile = (_REPO_ROOT / "docker" / "backend" / "Dockerfile").read_text(
            encoding="utf-8"
        )
        assert "BUILDER REDIS OK" in dockerfile
        assert "RUNTIME REDIS OK" in dockerfile
        assert "pip show redis" in dockerfile
        assert "import redis" in dockerfile


class TestRedisAdapterAndStack:
    """RedisCachePort and try_build_redis_stack construction."""

    def test_redis_cache_port_with_mock_client(self, monkeypatch) -> None:
        mock_redis = MagicMock()
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis.Redis.from_url.return_value = mock_client

        from production_platform.adapters import redis_stack
        monkeypatch.setattr(redis_stack, "_load_redis", lambda: mock_redis)

        cache = RedisCachePort("redis://127.0.0.1:6379/0", key_prefix="test")
        mock_client.get.return_value = b'{"foo": "bar"}'
        assert cache.get("testkey") == {"foo": "bar"}

        cache.set("testkey", {"foo": "bar"}, ttl_seconds=60)
        mock_client.setex.assert_called_once()

    def test_try_build_redis_stack_success(self, monkeypatch) -> None:
        mock_redis = MagicMock()
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis.Redis.from_url.return_value = mock_client

        from production_platform.adapters import redis_stack
        monkeypatch.setattr(redis_stack, "_load_redis", lambda: mock_redis)

        stack = try_build_redis_stack("redis://127.0.0.1:6379/0")
        assert stack is not None
        assert "cache" in stack
        assert "rate_limit" in stack
        assert "lock" in stack
        assert "session" in stack

    def test_try_build_redis_stack_none_on_empty_url(self) -> None:
        assert try_build_redis_stack(None) is None
        assert try_build_redis_stack("") is None

    def test_try_build_redis_stack_logs_and_returns_none_on_failure(self, monkeypatch) -> None:
        from production_platform.adapters import redis_stack
        def _fail():
            raise ImportError("No module named redis")
        monkeypatch.setattr(redis_stack, "_load_redis", _fail)

        stack = try_build_redis_stack("redis://127.0.0.1:6379/0")
        assert stack is None


class TestRequiredRedisBehavior:
    """When fallback is false and Redis is unavailable, must NOT claim Redis active."""

    def test_production_does_not_claim_redis_healthy_when_unavailable(self) -> None:
        """With fallback=False and dead redis URL, diagnostics must show fail."""
        infra = InfrastructureBundle.from_environment(
            environ={
                "DSP_ENVIRONMENT": "production",
                "DSP_REDIS_URL": "redis://127.0.0.1:1/0",
                "DSP_REDIS_FALLBACK": "false",
                "DSP_REDIS_TIMEOUT": "0.05",
            }
        )
        health = infra.health_check()
        assert health["redis"]["status"] == "fail"
        assert health["redis"]["fallback_active"] is False
        assert infra.diagnostics.redis_fallback_active is False
        assert any("graceful_fallback=false" in note for note in infra.notes)


class TestHealthAndOfflineBehavior:
    """Health reporting and offline support."""

    def test_health_reports_redis_pass_when_redis_selected(self) -> None:
        diag = InfrastructureDiagnostics(
            database_adapter="PostgresDatabasePort",
            cache_adapter="RedisCachePort",
            rate_limit_adapter="RedisRateLimitPort",
            lock_adapter="RedisLockPort",
            session_adapter="RedisSessionPort",
            storage_adapter="InMemoryStoragePort",
            job_queue_adapter="InMemoryJobQueuePort",
            secrets_adapter="InMemorySecretsPort",
            redis_fallback_active=False,
        )
        cfg = ProductionConfiguration(
            environment=Environment.PRODUCTION,
            redis=RedisSettings(url="redis://redis:6379/0", graceful_fallback=False),
        )
        bundle = InfrastructureBundle(
            configuration=ConfigurationManager(cfg),
            database=MagicMock(),
            repositories=MagicMock(),
            cache=MagicMock(),
            rate_limit=MagicMock(),
            lock=MagicMock(),
            session=MagicMock(),
            storage=MagicMock(),
            job_queue=MagicMock(),
            background_tasks=MagicMock(),
            clock=MagicMock(),
            secrets=MagicMock(),
            diagnostics=diag,
        )
        health = bundle.health_check()
        assert health["redis"]["configured"] is True
        assert health["redis"]["status"] == "pass"
        assert health["redis"]["fallback_active"] is False

    def test_offline_preserves_in_memory_cache(self) -> None:
        infra = InfrastructureBundle.from_environment(force_offline=True)
        assert isinstance(infra.cache, InMemoryCachePort)
        assert infra.diagnostics.cache_adapter == "InMemoryCachePort"
