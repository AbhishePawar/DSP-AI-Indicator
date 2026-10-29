#!/usr/bin/env bash
# EPIC-P7.0 — Deploy DSP AI Indicator production stack.
#
# Release images are immutable: every deploy builds images tagged
# "<VERSION>-<12-char git SHA>" from a clean checkout, refuses to overwrite an
# existing tag, and records image IDs of the last two known-good releases so
# scripts/rollback_production.sh can restore the exact previous application.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT}/docker/docker-compose.production.yml"
ENV_FILE="${ROOT}/.env.production"
RELEASE_DIR="${ROOT}/.dsp_production_releases"
CURRENT_GOOD="${RELEASE_DIR}/known_good_current.env"
PREVIOUS_GOOD="${RELEASE_DIR}/known_good_previous.env"

cd "${ROOT}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[deploy] Missing ${ENV_FILE}" >&2
  echo "[deploy] Copy .env.production.example → .env.production and fill secrets." >&2
  exit 1
fi

# Unquoted values containing spaces make `source` run the remainder as a
# command (e.g. "www.example.com: command not found") and silently drop the
# variable. Refuse before sourcing.
if grep -nE '^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=[^"'"'"'[:space:]#][^[:space:]]*[[:space:]]+[^#[:space:]]' "${ENV_FILE}" \
  | cut -d= -f1 >&2; then
  echo "[deploy] ${ENV_FILE}: the variables above have unquoted values containing spaces." >&2
  echo "[deploy] DSP_PUBLIC_DOMAIN must be one hostname; use DSP_WWW_REDIRECT_DOMAIN for www." >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
# shellcheck source=/dev/null
source "${ENV_FILE}"
set +a

# --- Immutable release identity (derived from git; the env file cannot pin it)
if ! GIT_SHA_FULL="$(git -C "${ROOT}" rev-parse --verify HEAD 2>/dev/null)"; then
  echo "[deploy] FAILED: ${ROOT} is not a git checkout; cannot derive an immutable image tag" >&2
  exit 1
fi
if [[ -n "$(git -C "${ROOT}" status --porcelain)" ]]; then
  git -C "${ROOT}" status --short >&2
  echo "[deploy] FAILED: working tree has uncommitted or untracked files (listed above)." >&2
  echo "[deploy] The image tag must describe exactly the committed code. Commit or remove them first." >&2
  exit 1
fi
APP_VERSION="$(tr -d '[:space:]' < "${ROOT}/VERSION")"
RELEASE_TAG="${APP_VERSION}-${GIT_SHA_FULL:0:12}"
if [[ ! "${RELEASE_TAG}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]]; then
  echo "[deploy] FAILED: derived image tag '${RELEASE_TAG}' is not a valid Docker tag" >&2
  exit 1
fi

for var in DSP_IMAGE_TAG DSP_IMAGE_TAG_WEB DSP_MARKET_GATEWAY_TAG; do
  if [[ -n "${!var:-}" && "${!var}" != "${RELEASE_TAG}" ]]; then
    echo "[deploy] note: ${var}=${!var} in ${ENV_FILE} is ignored; release tag is ${RELEASE_TAG}"
  fi
done
export DSP_IMAGE_TAG="${RELEASE_TAG}"
export DSP_IMAGE_TAG_WEB="${RELEASE_TAG}"
export DSP_MARKET_GATEWAY_TAG="${RELEASE_TAG}"
export GIT_SHA="${GIT_SHA_FULL}"

API_REPO="${DSP_API_IMAGE:-dsp-api}"
WEB_REPO="${DSP_WEB_IMAGE:-dsp-web}"
GATEWAY_REPO="${DSP_MARKET_GATEWAY_IMAGE:-dsp-market-data-gateway}"
API_REF="${API_REPO}:${RELEASE_TAG}"
WEB_REF="${WEB_REPO}:${RELEASE_TAG}"
GATEWAY_REF="${GATEWAY_REPO}:${RELEASE_TAG}"
GATEWAY_ENABLED=false
if [[ ",${COMPOSE_PROFILES:-}," == *",market-data,"* ]]; then
  GATEWAY_ENABLED=true
fi

compose() { docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"; }

echo "[deploy] validating production environment"
python "${ROOT}/scripts/validate_env.py" production

echo "[deploy] release ${RELEASE_TAG} (commit ${GIT_SHA_FULL})"
refs=("${API_REF}" "${WEB_REF}")
[[ "${GATEWAY_ENABLED}" == "true" ]] && refs+=("${GATEWAY_REF}")
for ref in "${refs[@]}"; do
  if docker image inspect "${ref}" >/dev/null 2>&1; then
    echo "[deploy] FAILED: image ${ref} already exists. Release tags are immutable and are never rebuilt." >&2
    echo "[deploy] To run this exact build again use: ./scripts/rollback_production.sh ${API_REF} ${WEB_REF}" >&2
    exit 1
  fi
done

mkdir -p "${RELEASE_DIR}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

# Pin a running service's image under a unique rollback tag and print its record.
pin_running() {
  local svc="$1" key="$2" repo="$3" cid id ref pin
  cid="$(compose ps -q "${svc}" 2>/dev/null | head -n1 || true)"
  [[ -z "${cid}" ]] && return 0
  id="$(docker inspect -f '{{.Image}}' "${cid}")"
  ref="$(docker inspect -f '{{.Config.Image}}' "${cid}")"
  pin="${id#sha256:}"
  pin="${repo}:rollback-${STAMP}-${pin:0:12}"
  docker tag "${id}" "${pin}"
  echo "${key}_REF=${pin}"
  echo "${key}_ID=${id}"
  echo "${key}_ORIGINAL_REF=${ref}"
}

if [[ ! -f "${CURRENT_GOOD}" ]]; then
  echo "[deploy] no known-good record yet: pinning the currently running release for rollback"
  {
    echo "RELEASE_TAG=pre-immutable-${STAMP}"
    echo "RECORDED_AT=${STAMP}"
    pin_running api API "${API_REPO}"
    pin_running web WEB "${WEB_REPO}"
    pin_running market-data-gateway GATEWAY "${GATEWAY_REPO}"
  } > "${CURRENT_GOOD}.tmp"
  if grep -q '^API_ID=' "${CURRENT_GOOD}.tmp" && grep -q '^WEB_ID=' "${CURRENT_GOOD}.tmp"; then
    mv -f "${CURRENT_GOOD}.tmp" "${CURRENT_GOOD}"
    echo "[deploy] pinned: $(grep -E '^(API|WEB)_REF=' "${CURRENT_GOOD}" | tr '\n' ' ')"
  else
    rm -f "${CURRENT_GOOD}.tmp"
    echo "[deploy] WARNING: api/web not running — first deploy has no rollback target" >&2
  fi
fi

echo "[deploy] building images ${API_REF} ${WEB_REF}"
compose build

for ref in "${refs[@]}"; do
  if ! docker image inspect "${ref}" >/dev/null 2>&1; then
    echo "[deploy] FAILED: build did not produce ${ref}" >&2
    exit 1
  fi
done

on_failure() {
  echo "[deploy] FAILED: release ${RELEASE_TAG} was not promoted." >&2
  echo "[deploy] Restore the last known-good release with: ./scripts/rollback_production.sh" >&2
}

echo "[deploy] starting stack"
if ! compose up -d --no-build --remove-orphans; then
  on_failure
  exit 1
fi

echo "[deploy] waiting for API health"
API_READY=false
for _ in $(seq 1 60); do
  if compose exec -T api curl -fsS "http://127.0.0.1:8000/health/ready" >/dev/null 2>&1; then
    echo "[deploy] API ready"
    API_READY=true
    break
  fi
  sleep 2
done
if [[ "${API_READY}" != "true" ]]; then
  echo "[deploy] API did not become ready within 120s" >&2
  on_failure
  exit 1
fi

echo "[deploy] waiting for web health"
WEB_READY=false
for _ in $(seq 1 60); do
  if compose exec -T web wget -qO- "http://127.0.0.1:3000/api/health" >/dev/null 2>&1; then
    echo "[deploy] Web ready"
    WEB_READY=true
    break
  fi
  sleep 2
done
if [[ "${WEB_READY}" != "true" ]]; then
  echo "[deploy] web did not become ready within 120s" >&2
  on_failure
  exit 1
fi

DOMAIN="${DSP_PUBLIC_DOMAIN:-localhost}"
echo "[deploy] smoke (internal)"
if ! compose exec -T api curl -fsS "http://127.0.0.1:8000/health" >/dev/null \
  || ! compose exec -T api curl -fsS "http://127.0.0.1:8000/metrics" >/dev/null; then
  on_failure
  exit 1
fi

if [[ "${DSP_SMOKE_REQUIRE_HTTPS:-true}" == "true" && "${DOMAIN}" != "localhost" ]]; then
  echo "[deploy] external HTTPS smoke → https://${DOMAIN}"
  if ! curl -fsS "https://${DOMAIN}/api/health" >/dev/null; then
    echo "[deploy] external HTTPS smoke failed — check DNS/ACME (set DSP_SMOKE_REQUIRE_HTTPS=false only for non-public dry runs)" >&2
    on_failure
    exit 1
  fi
fi

# Confirm the containers really run the images built for this commit.
running_id() { docker inspect -f '{{.Image}}' "$(compose ps -q "$1" | head -n1)"; }
API_ID="$(docker image inspect -f '{{.Id}}' "${API_REF}")"
WEB_ID="$(docker image inspect -f '{{.Id}}' "${WEB_REF}")"
if [[ "$(running_id api)" != "${API_ID}" || "$(running_id web)" != "${WEB_ID}" ]]; then
  echo "[deploy] running containers do not use ${API_REF} / ${WEB_REF}" >&2
  on_failure
  exit 1
fi

# Promote: only after every gate passed.
{
  echo "RELEASE_TAG=${RELEASE_TAG}"
  echo "GIT_SHA=${GIT_SHA_FULL}"
  echo "RECORDED_AT=${STAMP}"
  echo "API_REF=${API_REF}"
  echo "API_ID=${API_ID}"
  echo "WEB_REF=${WEB_REF}"
  echo "WEB_ID=${WEB_ID}"
  if [[ "${GATEWAY_ENABLED}" == "true" ]]; then
    echo "GATEWAY_REF=${GATEWAY_REF}"
    echo "GATEWAY_ID=$(docker image inspect -f '{{.Id}}' "${GATEWAY_REF}")"
  fi
} > "${CURRENT_GOOD}.next"
if [[ -f "${CURRENT_GOOD}" ]]; then
  mv -f "${CURRENT_GOOD}" "${PREVIOUS_GOOD}"
fi
mv -f "${CURRENT_GOOD}.next" "${CURRENT_GOOD}"

echo "[deploy] OK — production stack is up"
echo "[deploy] Domain: ${DOMAIN}"
echo "[deploy] Images: api=${API_REF} web=${WEB_REF}"
echo "[deploy] Commit: ${GIT_SHA_FULL}"
