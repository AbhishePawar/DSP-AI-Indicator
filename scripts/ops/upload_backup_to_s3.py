#!/usr/bin/env python3
"""Upload a verified local PostgreSQL backup and checksum to the S3 offsite bucket.

Credentials are resolved by boto3's standard chain (prefer the VPS instance role).
This command never deletes local backups or existing S3 objects.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "Usage: upload_backup_to_s3.py /path/to/dsp_pg_<UTC>.sql.gz",
            file=sys.stderr,
        )
        return 2

    bucket = os.environ.get("DSP_BACKUP_S3_BUCKET", "").strip()
    region = os.environ.get("DSP_BACKUP_S3_REGION", "").strip()
    if not bucket or bucket.startswith("CHANGE_ME_"):
        print(
            "FAIL: set DSP_BACKUP_S3_BUCKET to the verified existing backup bucket.",
            file=sys.stderr,
        )
        return 2
    if not region:
        print("FAIL: DSP_BACKUP_S3_REGION must be set.", file=sys.stderr)
        return 2

    archive = Path(sys.argv[1]).resolve()
    if not archive.is_file() or archive.stat().st_size < 64:
        print("FAIL: backup archive is missing or too small.", file=sys.stderr)
        return 2
    checksum = archive.with_name(archive.name + ".sha256")
    hasher = hashlib.sha256()
    with archive.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    if not checksum.is_file():
        print(
            "FAIL: local SHA-256 sidecar is missing; refusing upload.",
            file=sys.stderr,
        )
        return 2
    recorded = checksum.read_text(encoding="utf-8").split()[0].strip().lower()
    if recorded != digest:
        print(
            "FAIL: local SHA-256 sidecar does not match the archive.",
            file=sys.stderr,
        )
        return 2

    environment = os.environ.get("DSP_ENVIRONMENT", "development").strip().lower()
    default_prefix = f"backups/{environment}/postgres"
    prefix = os.environ.get("DSP_BACKUP_S3_PREFIX", default_prefix).strip("/")
    key = f"{prefix}/{archive.name}" if prefix else archive.name
    checksum_key = f"{key}.sha256"

    try:
        import boto3

        client = boto3.client("s3", region_name=region)
        client.upload_file(
            str(archive),
            bucket,
            key,
            ExtraArgs={"Metadata": {"sha256": digest}},
        )
        client.upload_file(str(checksum), bucket, checksum_key)
        head = client.head_object(Bucket=bucket, Key=key)
        metadata_digest = head.get("Metadata", {}).get("sha256")
        if metadata_digest and metadata_digest != digest:
            raise RuntimeError("uploaded archive SHA-256 metadata mismatch")
        print(
            "PASS: offsite backup uploaded and verified; "
            f"bucket={bucket}; region={region}; key={key}"
        )
        print(f"PASS: checksum uploaded; key={checksum_key}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(
            "FAIL: S3 offsite backup upload/verification failed: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
