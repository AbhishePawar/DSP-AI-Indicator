#!/usr/bin/env bash
# EPIC-P7.0 — Roll production back to a recorded known-good release.
#
# Usage:
#   ./scripts/rollback_production.sh                  # automatic target
#   ./scripts/rollback_production.sh <api_ref> <web_ref>
#
# Automatic target: if the running api/web are the last known-good release,
# go to the release before it; otherwise (a failed deploy) go back to the last
# known-good release. Image IDs are verified before and after the switch, and
# images are never rebuilt during rollback.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT}/docker/docker-compose.production.yml"
ENV_FILE="${ROOT}/.env.production"
RELEASE_DIR="${ROOT}/.dsp_production_releases"
CURRENT_GOOD="${RELEASE_DIR}/known_good_current.env"
PREVIOUS_GOOD="${RELEASE_DIR}/known_good_previous.env"

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

compose() { docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"; }
running_id() {
  local cid
  cid="$(compose ps -q "$1" 2>/dev/null | head -n1 || true)"
  [[ -n "${cid}" ]] && docker inspect -f '{{.Image}}' "${cid}"
  return 0
}
record_value() { grep -E "^$2=" "$1" | tail -n1 | cut -d= -f2-; }

TARGET_API_REF="" TARGET_WEB_REF="" TARGET_API_ID="" TARGET_WEB_ID="" TARGET_LABEL=""
if [[ $# -ge 2 ]]; then
  TARGET_API_REF="$1"
  TARGET_WEB_REF="$2"
  TARGET_LABEL="explicit"
elif [[ $# -ne 0 ]]; then
  echo "[rollback] Usage: $0 [<api_image_ref> <web_image_ref>]" >&2
  exit 1
else
  if [[ ! -f "${CURRENT_GOOD}" ]]; then
    echo "[rollback] FAILED: no known-good release record in ${RELEASE_DIR}" >&2
    echo "[rollback] Pass image references explicitly: $0 <api_ref> <web_ref>" >&2
    exit 1
  fi
  RECORD="${CURRENT_GOOD}"
  if [[ "$(running_id api)" == "$(record_value "${CURRENT_GOOD}" API_ID)" \
     && "$(running_id web)" == "$(record_value "${CURRENT_GOOD}" WEB_ID)" ]]; then
    if [[ ! -f "${PREVIOUS_GOOD}" ]]; then
      echo "[rollback] FAILED: already on the only known-good release; nothing older is recorded" >&2
      exit 1
    fi
    RECORD="${PREVIOUS_GOOD}"
  fi
  TARGET_API_REF="$(record_value "${RECORD}" API_REF)"
  TARGET_WEB_REF="$(record_value "${RECORD}" WEB_REF)"
  TARGET_API_ID="$(record_value "${RECORD}" API_ID)"
  TARGET_WEB_ID="$(record_value "${RECORD}" WEB_ID)"
  TARGET_LABEL="$(record_value "${RECORD}" RELEASE_TAG)"
fi

for ref in "${TARGET_API_REF}" "${TARGET_WEB_REF}"; do
  if [[ "${ref}" != *:* ]]; then
    echo "[rollback] FAILED: '${ref}' is not an image reference (repo:tag)" >&2
    exit 1
  fi
done

# Verify the images still exist and are byte-identical to what was recorded.
API_ID_NOW="$(docker image inspect -f '{{.Id}}' "${TARGET_API_REF}" 2>/dev/null || true)"
WEB_ID_NOW="$(docker image inspect -f '{{.Id}}' "${TARGET_WEB_REF}" 2>/dev/null || true)"
if [[ -z "${API_ID_NOW}" || -z "${WEB_ID_NOW}" ]]; then
  echo "[rollback] FAILED: target image missing locally (${TARGET_API_REF} / ${TARGET_WEB_REF})" >&2
  exit 1
fi
if [[ -n "${TARGET_API_ID}" && "${API_ID_NOW}" != "${TARGET_API_ID}" ]] \
   || [[ -n "${TARGET_WEB_ID}" && "${WEB_ID_NOW}" != "${TARGET_WEB_ID}" ]]; then
  echo "[rollback] FAILED: target tag now points at a different image than recorded — refusing" >&2
  exit 1
fi

echo "[rollback] rolling back to ${TARGET_LABEL}: api=${TARGET_API_REF} web=${TARGET_WEB_REF}"
export DSP_API_IMAGE="${TARGET_API_REF%:*}"
export DSP_IMAGE_TAG="${TARGET_API_REF##*:}"
export DSP_WEB_IMAGE="${TARGET_WEB_REF%:*}"
export DSP_IMAGE_TAG_WEB="${TARGET_WEB_REF##*:}"

compose up -d --no-build api web proxy

echo "[rollback] verifying health"
ok=false
for _ in $(seq 1 60); do
  if compose exec -T api curl -fsS "http://127.0.0.1:8000/health/ready" >/dev/null 2>&1 \
     && compose exec -T web wget -qO- "http://127.0.0.1:3000/api/health" >/dev/null 2>&1; then
    ok=true
    break
  fi
  sleep 2
done
if [[ "${ok}" != "true" ]]; then
  echo "[rollback] FAILED: rolled-back stack did not become healthy within 120s" >&2
  exit 1
fi

if [[ "$(running_id api)" != "${API_ID_NOW}" || "$(running_id web)" != "${WEB_ID_NOW}" ]]; then
  echo "[rollback] FAILED: running containers do not use the target images" >&2
  exit 1
fi

echo "[rollback] OK — api=${API_ID_NOW} web=${WEB_ID_NOW}"
