#!/usr/bin/env bash
# EPIC-P7.0 — Restore production database (destructive).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT}/.env.production"
COMPOSE_FILE="${ROOT}/docker/docker-compose.production.yml"
ARCHIVE="${1:-}"

cd "${ROOT}"

if [[ -z "${ARCHIVE}" || ! -f "${ARCHIVE}" ]]; then
  echo "Usage: $0 <dsp_pg_YYYYMMDDTHHMMSSZ.sql.gz>" >&2
  exit 1
fi

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "${ENV_FILE}"
  set +a
fi

if [[ -f "${ARCHIVE}.sha256" ]]; then
  echo "[restore] verifying checksum"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c "${ARCHIVE}.sha256"
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -c "${ARCHIVE}.sha256"
  fi
fi

CONFIRM="${DSP_RESTORE_CONFIRM:-}"
if [[ "${CONFIRM}" != "YES" ]]; then
  echo "[restore] Refusing without DSP_RESTORE_CONFIRM=YES" >&2
  exit 1
fi

if docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" ps postgres 2>/dev/null | grep -q "running\|Up"; then
  echo "[restore] restoring into postgres container from ${ARCHIVE}"
  gunzip -c "${ARCHIVE}" | docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T postgres \
    sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
  echo "[restore] OK — verify /health/ready and run smoke"
  exit 0
fi

exec "${ROOT}/scripts/ops/restore_postgres.sh" "${ARCHIVE}"
