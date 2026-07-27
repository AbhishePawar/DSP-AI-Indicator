#!/bin/sh
set -eu

echo "[dsp-api] Starting API (RC1) — graceful shutdown enabled"
exec uvicorn api_platform.api.app:app \
  --host "${DSP_API_HOST:-0.0.0.0}" \
  --port "${DSP_API_PORT:-8000}" \
  --timeout-graceful-shutdown "${DSP_GRACEFUL_SHUTDOWN_SECONDS:-30}" \
  --proxy-headers \
  --forwarded-allow-ips="${DSP_FORWARDED_ALLOW_IPS:-*}"
