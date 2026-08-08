#!/usr/bin/env bash
# P1.1 — Restore a PostgreSQL logical backup created by backup_postgres.sh.
# WARNING: destructive to the target database. Confirm before running in prod.
set -euo pipefail

ARCHIVE="${1:-}"
if [[ -z "${ARCHIVE}" || ! -f "${ARCHIVE}" ]]; then
  echo "Usage: $0 <dsp_pg_YYYYMMDDTHHMMSSZ.sql.gz>" >&2
  exit 1
fi

if [[ -f "${ARCHIVE}.sha256" ]]; then
  echo "[restore] verifying checksum"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c "${ARCHIVE}.sha256"
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -c "${ARCHIVE}.sha256"
  fi
fi

if [[ -z "${DSP_DATABASE_URL:-}" && -z "${PGDATABASE:-}" ]]; then
  echo "Set DSP_DATABASE_URL or standard PG* variables" >&2
  exit 1
fi

echo "[restore] restoring ${ARCHIVE}"
if [[ -n "${DSP_DATABASE_URL:-}" ]]; then
  gunzip -c "${ARCHIVE}" | psql "${DSP_DATABASE_URL}"
else
  gunzip -c "${ARCHIVE}" | psql
fi

echo "[restore] OK — run /health/ready and application smoke next"
