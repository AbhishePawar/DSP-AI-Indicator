#!/usr/bin/env bash
# EPIC-P7.4 — Frequent (incremental cadence) logical Postgres dump.
# Still a logical pg_dump — not physical WAL. Use to tighten practical RPO when PITR unavailable.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=backup_postgres.sh
# Reuse full dump mechanics with an incr filename prefix via env.
export DSP_BACKUP_PREFIX="${DSP_BACKUP_PREFIX:-dsp_pg_incr}"
export DSP_BACKUP_DIR="${DSP_BACKUP_DIR:-/var/backups/dsp}"

if [[ ! -x "${ROOT}/scripts/ops/backup_postgres.sh" ]]; then
  chmod +x "${ROOT}/scripts/ops/backup_postgres.sh" || true
fi

# Prefer dedicated incr wrapper around the same dump tool.
if [[ -z "${DSP_DATABASE_URL:-}" ]]; then
  echo "DSP_DATABASE_URL is required" >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${DSP_BACKUP_DIR}/${DSP_BACKUP_PREFIX}_${STAMP}.sql.gz"
mkdir -p "${DSP_BACKUP_DIR}"

echo "[incr] dumping to ${OUT}"
# shellcheck disable=SC2086
pg_dump "${DSP_DATABASE_URL}" | gzip -c > "${OUT}"
BYTES="$(wc -c < "${OUT}" | tr -d ' ')"
if [[ "${BYTES}" -lt 64 ]]; then
  echo "[incr] dump too small (${BYTES} bytes)" >&2
  exit 1
fi
sha256sum "${OUT}" | awk '{print $1}' > "${OUT}.sha256"
echo "[incr] ok bytes=${BYTES} sha256=$(cat "${OUT}.sha256")"

# Retention: keep last 48 incr files
ls -1t "${DSP_BACKUP_DIR}/${DSP_BACKUP_PREFIX}_"*.sql.gz 2>/dev/null | tail -n +49 | while read -r old; do
  rm -f "${old}" "${old}.sha256" || true
done
