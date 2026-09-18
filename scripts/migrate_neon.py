"""Apply the DSP-owned PostgreSQL schema without touching Neon Auth."""

from __future__ import annotations

import os
import sys

from production_platform.adapters.postgres import build_postgres
from production_platform.production.schema import apply_application_schema


def main() -> int:
    dsn = os.environ.get("DSP_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DSP_DATABASE_URL or DATABASE_URL must be set")
    if "sslmode=" not in dsn.lower():
        raise SystemExit("Refusing to migrate without an explicit PostgreSQL sslmode")

    database = build_postgres(
        dsn,
        application_name=os.environ.get("DSP_DATABASE_APPLICATION_NAME", "dsp-migrate"),
    )
    applied = apply_application_schema(database)
    print("Applied migrations:" if applied else "Schema already current")
    for version in applied:
        print(version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
