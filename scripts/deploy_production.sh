#!/usr/bin/env bash
# EPIC-P7.0 — Deploy DSP AI Indicator production stack.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT}/docker/docker-compose.vps.yml"
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

if [[ -n "${DSP_PREVIOUS_IMAGE_TAG:-}" && "${DSP_PREVIOUS_IMAGE_TAG}" == "${DSP_IMAGE_TAG:-}" ]]; then
  echo "[deploy] ERROR: API image tag must differ from the previous known-good tag" >&2
  exit 1
fi
if [[ -n "${DSP_PREVIOUS_IMAGE_TAG_WEB:-}" && "${DSP_PREVIOUS_IMAGE_TAG_WEB}" == "${DSP_IMAGE_TAG_WEB:-}" ]]; then
  echo "[deploy] ERROR: web image tag must differ from the previous known-good tag" >&2
  exit 1
fi
if [[ "${DSP_IMAGE_TAG:-}" =~ ^(latest|stable|main)$ || "${DSP_IMAGE_TAG_WEB:-}" =~ ^(latest|stable|main)$ ]]; then
  echo "[deploy] ERROR: use immutable version tags, not latest/stable/main" >&2
  exit 1
fi

echo "[deploy] validating Compose configuration"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" config --quiet

echo "[deploy] recording explicitly configured previous image tags (for rollback)"
{
  echo "DSP_IMAGE_TAG=${DSP_PREVIOUS_IMAGE_TAG:-}"
  echo "DSP_IMAGE_TAG_WEB=${DSP_PREVIOUS_IMAGE_TAG_WEB:-}"
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
API_READY=false
for _ in $(seq 1 60); do
  if docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T api \
    curl -fsS "http://127.0.0.1:8000/health/ready" >/dev/null 2>&1; then
    API_READY=true
    echo "[deploy] API ready"
    break
  fi
  sleep 2
done
if [[ "${API_READY}" != "true" ]]; then
  echo "[deploy] ERROR: API did not become healthy; recent logs follow" >&2
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" logs --tail=100 api >&2 || true
  exit 1
fi

echo "[deploy] waiting for web health"
WEB_READY=false
for _ in $(seq 1 60); do
  if docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T web \
    wget -qO- "http://127.0.0.1:3000/api/health" >/dev/null 2>&1; then
    WEB_READY=true
    echo "[deploy] Web ready"
    break
  fi
  sleep 2
done
if [[ "${WEB_READY}" != "true" ]]; then
  echo "[deploy] ERROR: web did not become healthy; recent logs follow" >&2
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" logs --tail=100 web >&2 || true
  exit 1
fi

mv -f "${PREV_TAG_FILE}.next" "${PREV_TAG_FILE}"

DOMAIN="${DSP_PUBLIC_DOMAIN:-localhost}"
echo "[deploy] smoke (internal)"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T api \
  curl -fsS "http://127.0.0.1:8000/health" >/dev/null
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T api \
  curl -fsS "http://127.0.0.1:8000/metrics" >/dev/null

if [[ "${DSP_SMOKE_REQUIRE_HTTPS:-true}" == "true" && "${DOMAIN}" != "localhost" ]]; then
  echo "[deploy] external HTTPS smoke → https://${DOMAIN}"
  curl --retry 5 --retry-delay 2 --retry-connrefused -fsS "https://${DOMAIN}/api/health" >/dev/null
fi

echo "[deploy] OK — production stack is up"
echo "[deploy] Domain: ${DOMAIN}"
echo "[deploy] Images: api=${DSP_IMAGE_TAG:-1.7.0} web=${DSP_IMAGE_TAG_WEB:-2.0.0}"
