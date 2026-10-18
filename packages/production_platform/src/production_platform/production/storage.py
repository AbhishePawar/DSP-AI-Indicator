"""Object storage — in-memory + local filesystem (PEP-002)."""

from __future__ import annotations

import errno
import shutil
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from production_platform.production.exceptions import ConfigurationError, ProviderError
from production_platform.production.interfaces import StoragePort

__all__ = [
    "InMemoryStoragePort",
    "LocalFilesystemStoragePort",
    "LocalFirstS3OverflowStoragePort",
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


class LocalFirstS3OverflowStoragePort(LocalFilesystemStoragePort):
    """Local-first storage; send only new objects to S3 at the disk threshold.

    Existing local files are never migrated or deleted by this adapter. S3
    objects use a dedicated prefix and are read only when the local key is absent.
    If local storage reaches the threshold without a working S3 adapter, new
    writes fail explicitly rather than silently consuming the remaining disk.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        overflow_storage: StoragePort | None = None,
        threshold: float = 0.95,
        prefix: str = "overflow",
    ) -> None:
        super().__init__(root)
        if not 0 < threshold < 1:
            raise ConfigurationError(
                "storage overflow threshold must be between 0 and 1"
            )
        self._overflow_storage = overflow_storage
        self._overflow_verified = False
        self._overflow_threshold = threshold
        self._overflow_prefix = prefix.strip("/")

    @property
    def overflow_available(self) -> bool:
        """True only after this process has completed a successful S3 operation."""
        return self._overflow_storage is not None and self._overflow_verified

    def _overflow_key(self, key: str) -> str:
        cleaned = key.replace("\\", "/").lstrip("/")
        if ".." in cleaned.split("/"):
            raise ProviderError("invalid object key")
        if self._overflow_prefix:
            return f"{self._overflow_prefix}/{cleaned}"
        return cleaned

    def _disk_threshold_reached(self) -> bool:
        usage = shutil.disk_usage(self._root)
        return usage.total > 0 and usage.used / usage.total >= self._overflow_threshold

    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        target = self._resolve(key)
        # Never relocate/overflow an existing local file: updates remain local.
        if target.is_file():
            try:
                super().put(key, data, content_type=content_type)
            except OSError as exc:
                if exc.errno == errno.ENOSPC:
                    raise ProviderError(
                        "local disk is full while updating an existing local object; "
                        "existing files were not moved to S3"
                    ) from exc
                raise
            return

        if self._disk_threshold_reached():
            if self._overflow_storage is None:
                raise ProviderError(
                    "local artifact storage reached the 95% overflow threshold, "
                    "but DSP_BACKUP_S3_BUCKET is not configured or S3 is unavailable"
                )
            self._overflow_storage.put(
                self._overflow_key(key), data, content_type=content_type
            )
            self._overflow_verified = True
            return

        try:
            super().put(key, data, content_type=content_type)
        except OSError as exc:
            if exc.errno != errno.ENOSPC:
                raise
            # This was a new key, so any partial file was created by this failed
            # write. Remove only that partial file before falling back to S3.
            target.unlink(missing_ok=True)
            if self._overflow_storage is None:
                raise ProviderError(
                    "local disk is full and S3 overflow storage is unavailable"
                ) from exc
            self._overflow_storage.put(
                self._overflow_key(key), data, content_type=content_type
            )
            self._overflow_verified = True

    def get(self, key: str) -> bytes | None:
        local = super().get(key)
        if local is not None:
            return local
        if self._overflow_storage is None:
            return None
        result = self._overflow_storage.get(self._overflow_key(key))
        self._overflow_verified = True
        return result

    def delete(self, key: str) -> None:
        target = self._resolve(key)
        if target.is_file():
            super().delete(key)
            return
        if self._overflow_storage is not None:
            self._overflow_storage.delete(self._overflow_key(key))
            self._overflow_verified = True


def ensure_storage_port(port: StoragePort | None) -> StoragePort:
    return port if port is not None else InMemoryStoragePort()
