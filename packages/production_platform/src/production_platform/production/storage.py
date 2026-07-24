"""Storage — in-memory provider-neutral adapter."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from production_platform.production.interfaces import StoragePort

__all__ = ["InMemoryStoragePort", "StoredObject"]


@dataclass(frozen=True, slots=True)
class StoredObject:
    key: str
    data: bytes
    content_type: str | None


class InMemoryStoragePort:
    """Process-local blob map — not S3 / Azure / GCS."""

    def __init__(self) -> None:
        self._objects: dict[str, StoredObject] = {}
        self._lock = Lock()

    def put(
        self, key: str, data: bytes, *, content_type: str | None = None
    ) -> None:
        with self._lock:
            self._objects[key] = StoredObject(
                key=key, data=data, content_type=content_type
            )

    def get(self, key: str) -> bytes | None:
        with self._lock:
            obj = self._objects.get(key)
            return None if obj is None else obj.data

    def delete(self, key: str) -> None:
        with self._lock:
            self._objects.pop(key, None)

    def list_keys(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._objects))


def ensure_storage_port(port: StoragePort | None) -> StoragePort:
    return port if port is not None else InMemoryStoragePort()
