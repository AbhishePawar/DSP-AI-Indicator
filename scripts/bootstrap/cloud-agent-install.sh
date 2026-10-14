#!/usr/bin/env bash
# Cloud Agent install — idempotent bootstrap for the DSP AI Indicator monorepo.
# Prepares the Python backend (editable monorepo + dev/CI deps) and the
# Next.js thin-client web app, plus local-only env files. Safe to re-run.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "[install] Python backend — editable monorepo + dev/CI deps"
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[dev]"

echo "[install] Web frontend — npm dependencies (apps/web)"
if [ -f apps/web/package-lock.json ]; then
  ( cd apps/web && npm ci )
else
  ( cd apps/web && npm install )
fi

echo "[install] Local env files (never overwrite existing)"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "[install] created .env from .env.example"
fi
if [ ! -f apps/web/.env.local ]; then
  BUILD_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sed "s|^NEXT_PUBLIC_BUILD_TIMESTAMP=.*|NEXT_PUBLIC_BUILD_TIMESTAMP=${BUILD_TS}|" \
    apps/web/.env.example > apps/web/.env.local
  echo "[install] created apps/web/.env.local from .env.example"
fi

echo "[install] Done."
