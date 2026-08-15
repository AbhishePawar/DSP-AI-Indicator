#!/bin/sh
# EPIC-P7.3 — production-tuned API startup (ops only; no API contract changes)
set -eu

WORKERS="${DSP_UVICORN_WORKERS:-1}"
KEEPALIVE="${DSP_UVICORN_KEEPALIVE:-5}"
LIMIT_CONCURRENCY="${DSP_UVICORN_LIMIT_CONCURRENCY:-100}"
# Cloud Run injects PORT; keep DSP_API_PORT as an explicit override.
PORT="${PORT:-${DSP_API_PORT:-8000}}"
HOST="${DSP_API_HOST:-0.0.0.0}"

echo "[dsp-api] Starting API (P7.3) workers=${WORKERS} keepalive=${KEEPALIVE} bind=${HOST}:${PORT}"

# Single worker is the safe default (in-memory rate limits / beta state).
# Set DSP_UVICORN_WORKERS>1 only with shared Redis/session store.
if [ "${WORKERS}" = "1" ]; then
  exec uvicorn api_platform.api.app:app \
    --host "${HOST}" \
    --port "${PORT}" \
    --timeout-keep-alive "${KEEPALIVE}" \
    --limit-concurrency "${LIMIT_CONCURRENCY}" \
    --timeout-graceful-shutdown "${DSP_GRACEFUL_SHUTDOWN_SECONDS:-30}" \
    --proxy-headers \
    --forwarded-allow-ips="${DSP_FORWARDED_ALLOW_IPS:-*}"
fi

exec uvicorn api_platform.api.app:app \
  --host "${HOST}" \
  --port "${PORT}" \
  --workers "${WORKERS}" \
  --timeout-keep-alive "${KEEPALIVE}" \
  --limit-concurrency "${LIMIT_CONCURRENCY}" \
  --timeout-graceful-shutdown "${DSP_GRACEFUL_SHUTDOWN_SECONDS:-30}" \
  --proxy-headers \
  --forwarded-allow-ips="${DSP_FORWARDED_ALLOW_IPS:-*}"
