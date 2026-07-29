#!/usr/bin/env bash
# EPIC-P7.0 — Deploy DSP AI Indicator production stack.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT}/docker/docker-compose.production.yml"
ENV_FILE="${ROOT}/.env.production"
PREV_TAG_FILE="${ROOT}/.dsp_production_previous_tags"

cd "${ROOT}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[deploy] Missing ${ENV_FILE}" >&2
  echo "[deploy] Copy .env.production.example → .env.production and fill secrets." >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
# shellcheck source=/dev/null
source "${ENV_FILE}"
set +a

echo "[deploy] validating production environment"
python "${ROOT}/scripts/validate_env.py" production

echo "[deploy] recording previous image tags (for rollback)"
{
  echo "DSP_IMAGE_TAG=${DSP_IMAGE_TAG:-1.7.0}"
  echo "DSP_IMAGE_TAG_WEB=${DSP_IMAGE_TAG_WEB:-2.0.0}"
  echo "RECORDED_AT=$(date -u +%Y%m%dT%H%M%SZ)"
} > "${PREV_TAG_FILE}.next"
if [[ -f "${PREV_TAG_FILE}" ]]; then
  cp "${PREV_TAG_FILE}" "${PREV_TAG_FILE}.bak" || true
fi

echo "[deploy] building / pulling images"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" build

echo "[deploy] starting stack"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d --remove-orphans

echo "[deploy] waiting for API health"
for _ in $(seq 1 60); do
  if docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T api \
    curl -fsS "http://127.0.0.1:8000/health/ready" >/dev/null 2>&1; then
    echo "[deploy] API ready"
    break
  fi
  sleep 2
done

echo "[deploy] waiting for web health"
for _ in $(seq 1 60); do
  if docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T web \
    wget -qO- "http://127.0.0.1:3000/api/health" >/dev/null 2>&1; then
    echo "[deploy] Web ready"
    break
  fi
  sleep 2
done

mv -f "${PREV_TAG_FILE}.next" "${PREV_TAG_FILE}"

DOMAIN="${DSP_PUBLIC_DOMAIN:-localhost}"
echo "[deploy] smoke (internal)"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T api \
  curl -fsS "http://127.0.0.1:8000/health" >/dev/null
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T api \
  curl -fsS "http://127.0.0.1:8000/metrics" >/dev/null

if [[ "${DSP_SMOKE_REQUIRE_HTTPS:-true}" == "true" && "${DOMAIN}" != "localhost" ]]; then
  echo "[deploy] external HTTPS smoke → https://${DOMAIN}"
  curl -fsS "https://${DOMAIN}/api/health" >/dev/null || \
    echo "[deploy] WARN: external HTTPS smoke failed — check DNS/ACME" >&2
fi

echo "[deploy] OK — production stack is up"
echo "[deploy] Domain: ${DOMAIN}"
echo "[deploy] Images: api=${DSP_IMAGE_TAG:-1.7.0} web=${DSP_IMAGE_TAG_WEB:-2.0.0}"
