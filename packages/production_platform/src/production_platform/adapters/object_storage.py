"""S3-compatible object storage adapter (AWS S3 / MinIO) — lazy boto3."""

from __future__ import annotations

import importlib
from typing import Any

from production_platform.production.exceptions import ConfigurationError, ProviderError

__all__ = ["S3CompatibleStoragePort", "try_build_s3_storage"]


def _load_boto3() -> Any:
    try:
        return importlib.import_module("boto3")
    except ImportError as exc:
        raise ProviderError(
            "boto3 is not installed; pip install 'production-platform[s3]'"
        ) from exc


class S3CompatibleStoragePort:
    """StoragePort for S3 / MinIO via boto3 (lazy import)."""

    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str | None = None,
        region: str | None = None,
    ) -> None:
        if not bucket.strip():
            raise ConfigurationError("object storage bucket must not be empty")
        boto3 = _load_boto3()
        kwargs: dict[str, Any] = {}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        if region:
            kwargs["region_name"] = region
        try:
            self._client = boto3.client("s3", **kwargs)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"s3 client init failed: {exc}") from exc
        self._bucket = bucket

    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        extra: dict[str, Any] = {}
        if content_type:
            extra["ContentType"] = content_type
        try:
            self._client.put_object(Bucket=self._bucket, Key=key, Body=data, **extra)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"s3 put failed: {exc}") from exc

    def get(self, key: str) -> bytes | None:
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
            return resp["Body"].read()
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            if code in {"NoSuchKey", "404", "NotFound"}:
                return None
            # botocore ClientError 404
            if "NoSuchKey" in str(exc) or "Not Found" in str(exc):
                return None
            raise ProviderError(f"s3 get failed: {exc}") from exc

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"s3 delete failed: {exc}") from exc


def try_build_s3_storage(
    *,
    bucket: str | None,
    endpoint_url: str | None = None,
    region: str | None = None,
) -> S3CompatibleStoragePort | None:
    if not bucket:
        return None
    try:
        return S3CompatibleStoragePort(
            bucket=bucket, endpoint_url=endpoint_url, region=region
        )
    except (ConfigurationError, ProviderError, ImportError):
        return None
