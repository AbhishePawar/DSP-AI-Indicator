"""Optional vendor adapters (PEP-002).

Vendor SDKs are loaded via ``importlib`` so architecture scanners that forbid
static vendor imports remain valid. Engines must never import this package.
"""

from __future__ import annotations

from production_platform.adapters.object_storage import (
    S3CompatibleStoragePort,
    try_build_s3_storage,
)
from production_platform.adapters.postgres import (
    PostgresDatabasePort,
    try_build_postgres,
)
from production_platform.adapters.redis_stack import (
    RedisCachePort,
    RedisLockPort,
    RedisRateLimitPort,
    RedisSessionPort,
    try_build_redis_stack,
)

__all__ = [
    "PostgresDatabasePort",
    "RedisCachePort",
    "RedisLockPort",
    "RedisRateLimitPort",
    "RedisSessionPort",
    "S3CompatibleStoragePort",
    "try_build_postgres",
    "try_build_redis_stack",
    "try_build_s3_storage",
]
