#!/usr/bin/env bash
# Cloud Shell / CI helper — deploy Google-only email auth (backend + frontend).
# Prerequisites: gcloud authenticated; secrets exist:
#   dsp-google-client-id, dsp-google-client-secret
#   (plus existing dsp-auth-jwt-secret, dsp-resend-api-key, dsp-database-url)
set -euo pipefail
PROJECT="${PROJECT:-project-34de429e-3c43-4ae7-b75}"
REGION="${REGION:-asia-south1}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMMIT="$(git -C "$ROOT" rev-parse HEAD)"
SHORT="$(git -C "$ROOT" rev-parse --short=7 HEAD)"

echo "Deploying commit $COMMIT"

gcloud builds submit "$ROOT" \
  --config="$ROOT/cloudbuild.yaml" \
  --project="$PROJECT" \
  --substitutions="COMMIT_SHA=${COMMIT},SHORT_SHA=${SHORT}"

gcloud builds submit "$ROOT" \
  --config="$ROOT/cloudbuild-frontend.yaml" \
  --project="$PROJECT" \
  --substitutions="COMMIT_SHA=${COMMIT},SHORT_SHA=${SHORT}"

echo "Backend providers:"
curl -sS "https://dsp-ai-indicator-6uxsluxowq-el.a.run.app/api/v1/auth/enterprise/providers" | head -c 2000
echo
echo "Frontend login: https://dsp-ai-indicator-web-6uxsluxowq-el.a.run.app/login"
