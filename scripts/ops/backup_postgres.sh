#!/usr/bin/env bash
# P1.1 — Create a PostgreSQL logical backup for DSP.
# Requires: pg_dump, DSP_DATABASE_URL or PG* env vars.
set -euo pipefail

BACKUP_DIR="${DSP_BACKUP_DIR:-./backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "${BACKUP_DIR}"
OUT="${BACKUP_DIR}/dsp_pg_${STAMP}.sql.gz"

if [[ -z "${DSP_DATABASE_URL:-}" && -z "${PGDATABASE:-}" ]]; then
  echo "Set DSP_DATABASE_URL or standard PG* variables" >&2
  exit 1
fi

echo "[backup] writing ${OUT}"
if [[ -n "${DSP_DATABASE_URL:-}" && "${DSP_PG_CLIENT_USE_DOCKER:-true}" == "true" ]]; then
  command -v docker >/dev/null 2>&1 || {
    echo "Docker is required for the configured PostgreSQL client container" >&2
    exit 1
  }
  CLIENT_IMAGE="${DSP_PG_CLIENT_IMAGE:-postgres:18-alpine}"
  echo "[backup] using client image ${CLIENT_IMAGE}"
  docker run --rm --network host -e DSP_DATABASE_URL "${CLIENT_IMAGE}" \
    sh -lc 'pg_dump --no-owner --format=plain "$DSP_DATABASE_URL"' | gzip -c > "${OUT}"
elif [[ -n "${DSP_DATABASE_URL:-}" ]]; then
  command -v pg_dump >/dev/null 2>&1 || { echo "pg_dump not found; set DSP_PG_CLIENT_USE_DOCKER=true" >&2; exit 1; }
  pg_dump --no-owner --format=plain "${DSP_DATABASE_URL}" | gzip -c > "${OUT}"
else
  command -v pg_dump >/dev/null 2>&1 || { echo "pg_dump not found and DSP_DATABASE_URL is unset" >&2; exit 1; }
  pg_dump --no-owner --format=plain | gzip -c > "${OUT}"
fi

# Integrity marker: size + sha256
BYTES="$(wc -c < "${OUT}" | tr -d ' ')"
if [[ "${BYTES}" -lt 64 ]]; then
  echo "[backup] FAILED: archive too small (${BYTES} bytes)" >&2
  exit 1
fi
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "${OUT}" | tee "${OUT}.sha256"
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "${OUT}" | tee "${OUT}.sha256"
fi

echo "[backup] OK ${OUT} (${BYTES} bytes)"
echo "${OUT}"
