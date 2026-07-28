"""Object storage — in-memory + local filesystem (PEP-002)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from production_platform.production.exceptions import ConfigurationError, ProviderError
from production_platform.production.interfaces import StoragePort

__all__ = [
    "InMemoryStoragePort",
    "LocalFilesystemStoragePort",
    "StoredObject",
    "ensure_storage_port",
]


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

    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
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


class LocalFilesystemStoragePort:
    """Local directory object store — portable stand-in for S3/MinIO/GCS/Azure."""

    def __init__(self, root: str | Path) -> None:
        path = Path(root)
        if not str(root).strip():
            raise ConfigurationError("storage root must not be empty")
        path.mkdir(parents=True, exist_ok=True)
        self._root = path.resolve()

    def _resolve(self, key: str) -> Path:
        cleaned = key.replace("\\", "/").lstrip("/")
        if ".." in cleaned.split("/"):
            raise ProviderError("invalid object key")
        target = (self._root / cleaned).resolve()
        if not str(target).startswith(str(self._root)):
            raise ProviderError("object key escapes storage root")
        return target

    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        _ = content_type
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes | None:
        path = self._resolve(key)
        if not path.is_file():
            return None
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.is_file():
            path.unlink()


def ensure_storage_port(port: StoragePort | None) -> StoragePort:
    return port if port is not None else InMemoryStoragePort()
