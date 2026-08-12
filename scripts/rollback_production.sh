#!/usr/bin/env bash
# EPIC-P7.0 — Rollback production images to previous known-good tags.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT}/docker/docker-compose.production.yml"
ENV_FILE="${ROOT}/.env.production"
PREV_TAG_FILE="${ROOT}/.dsp_production_previous_tags"

cd "${ROOT}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[rollback] Missing ${ENV_FILE}" >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
# shellcheck source=/dev/null
source "${ENV_FILE}"
set +a

TARGET_API="${1:-${DSP_PREVIOUS_IMAGE_TAG:-}}"
TARGET_WEB="${2:-${DSP_PREVIOUS_IMAGE_TAG_WEB:-}}"

if [[ -z "${TARGET_API}" || -z "${TARGET_WEB}" ]]; then
  if [[ -f "${PREV_TAG_FILE}.bak" ]]; then
    # shellcheck disable=SC1090
    source "${PREV_TAG_FILE}.bak"
    TARGET_API="${DSP_IMAGE_TAG}"
    TARGET_WEB="${DSP_IMAGE_TAG_WEB}"
  fi
fi

if [[ -z "${TARGET_API}" || -z "${TARGET_WEB}" ]]; then
  echo "[rollback] Usage: $0 <api_tag> <web_tag>" >&2
  echo "[rollback] Or set DSP_PREVIOUS_IMAGE_TAG / DSP_PREVIOUS_IMAGE_TAG_WEB" >&2
  exit 1
fi

echo "[rollback] rolling back to api=${TARGET_API} web=${TARGET_WEB}"
export DSP_IMAGE_TAG="${TARGET_API}"
export DSP_IMAGE_TAG_WEB="${TARGET_WEB}"
export DSP_APP_VERSION="${TARGET_API}"

docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d api web proxy

echo "[rollback] verifying health"
sleep 5
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T api \
  curl -fsS "http://127.0.0.1:8000/health/ready" >/dev/null
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T web \
  wget -qO- "http://127.0.0.1:3000/api/health" >/dev/null

echo "[rollback] OK"
