#!/usr/bin/env bash
# EPIC-P7.0 — Production database backup (wraps ops/backup_postgres.sh).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT}/.env.production"
COMPOSE_FILE="${ROOT}/docker/docker-compose.production.yml"

cd "${ROOT}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "${ENV_FILE}"
  set +a
fi

BACKUP_DIR="${DSP_BACKUP_DIR:-${ROOT}/backups}"
mkdir -p "${BACKUP_DIR}"
export DSP_BACKUP_DIR="${BACKUP_DIR}"

# Prefer dump from running postgres container when available
if docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" ps postgres 2>/dev/null | grep -q "running\|Up"; then
  STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
  OUT="${BACKUP_DIR}/dsp_pg_${STAMP}.sql.gz"
  echo "[backup] dumping via postgres container → ${OUT}"
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T postgres \
    sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' | gzip -c > "${OUT}"
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
  exit 0
fi

exec "${ROOT}/scripts/ops/backup_postgres.sh"
