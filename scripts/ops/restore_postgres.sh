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
if [[ -n "${DSP_DATABASE_URL:-}" && "${DSP_PG_CLIENT_USE_DOCKER:-true}" == "true" ]]; then
  command -v docker >/dev/null 2>&1 || {
    echo "Docker is required for the configured PostgreSQL client container" >&2
    exit 1
  }
  CLIENT_IMAGE="${DSP_PG_CLIENT_IMAGE:-postgres:18-alpine}"
  echo "[restore] using client image ${CLIENT_IMAGE}"
  gunzip -c "${ARCHIVE}" | docker run --rm -i --network host -e DSP_DATABASE_URL "${CLIENT_IMAGE}" \
    sh -lc 'psql "$DSP_DATABASE_URL"'
elif [[ -n "${DSP_DATABASE_URL:-}" ]]; then
  command -v psql >/dev/null 2>&1 || { echo "psql not found; set DSP_PG_CLIENT_USE_DOCKER=true" >&2; exit 1; }
  gunzip -c "${ARCHIVE}" | psql "${DSP_DATABASE_URL}"
else
  command -v psql >/dev/null 2>&1 || { echo "psql not found and DSP_DATABASE_URL is unset" >&2; exit 1; }
  gunzip -c "${ARCHIVE}" | psql
fi

echo "[restore] OK — run /health/ready and application smoke next"
