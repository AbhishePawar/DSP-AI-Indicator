#!/usr/bin/env python3
"""Verify staging S3 write/read/delete using one unique, temporary object.

Run only on the staging VPS after setting DSP_ENVIRONMENT=staging,
DSP_BACKUP_S3_BUCKET and DSP_BACKUP_S3_REGION. Primary artifact storage
remains local; this script verifies only the separate offsite backup bucket.\nAWS credentials should come from the normal
boto3 credential chain (prefer the VPS role/instance profile); never pass
secrets on the command line.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-staging-s3-write",
        action="store_true",
        help="authorize a temporary write/read/delete test in the staging bucket",
    )
    args = parser.parse_args()

    environment = os.environ.get("DSP_ENVIRONMENT", "").strip().lower()
    bucket = os.environ.get("DSP_BACKUP_S3_BUCKET", "").strip()
    region = os.environ.get("DSP_BACKUP_S3_REGION", "").strip()

    if not args.confirm_staging_s3_write:
        print(\n            "REFUSED: pass --confirm-staging-s3-write to authorize the temporary test."\n        )
        return 2
    if environment != "staging":
        print("REFUSED: DSP_ENVIRONMENT must be exactly 'staging'.")
        return 2
    if not bucket or bucket.startswith("CHANGE_ME_"):
        print(\n            "REFUSED: set DSP_BACKUP_S3_BUCKET to the existing staging backup bucket."\n        )
        return 2
    if not region:
        print("REFUSED: DSP_BACKUP_S3_REGION must be set.")
        return 2

    key = f"ops-verification/{uuid.uuid4().hex}.txt"
    payload = f"DSP staging S3 verification {uuid.uuid4().hex}\n".encode("utf-8")
    client = None
    uploaded = False

    try:
        import boto3

        client = boto3.client("s3", region_name=region)
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=payload,
            ContentType="text/plain; charset=utf-8",
        )
        uploaded = True
        response = client.get_object(Bucket=bucket, Key=key)
        body = response["Body"].read()
        if body != payload:
            raise RuntimeError("S3 read-after-write payload mismatch")
        client.delete_object(Bucket=bucket, Key=key)
        uploaded = False
        try:
            client.head_object(Bucket=bucket, Key=key)
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            status = getattr(exc, "response", {}).get("ResponseMetadata", {}).get(
                "HTTPStatusCode"
            )
            if code in {"404", "NoSuchKey", "NotFound"} or status == 404:
                print(
                    f"PASS: S3 put/get/delete verified; bucket={bucket}; "
                    f"region={region}; key_prefix=ops-verification/"
                )
                return 0
            raise
        raise RuntimeError("S3 object still exists after delete")
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        if uploaded and client is not None:
            try:
                client.delete_object(Bucket=bucket, Key=key)
                print("Cleanup: removed the temporary verification object.")
            except Exception as cleanup_exc:  # noqa: BLE001
                print(
                    f"WARNING: temporary object cleanup failed "
                    f"({type(cleanup_exc).__name__}); key={key}",
                    file=sys.stderr,
                )


if __name__ == "__main__":
    raise SystemExit(main())
