#!/usr/bin/env bash
# Cloud Shell helper — deploy Google-only email auth (backend + frontend).
# Prerequisites: gcloud authenticated to project-34de429e-3c43-4ae7-b75
#
# Optional (required for functional Google OAuth):
#   echo -n 'YOUR_CLIENT_ID' | gcloud secrets create dsp-google-client-id --data-file=-
#   echo -n 'YOUR_CLIENT_SECRET' | gcloud secrets create dsp-google-client-secret --data-file=-
#   # or: gcloud secrets versions add ...
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
  --substitutions="COMMIT_SHA=${COMMIT}"

gcloud builds submit "$ROOT" \
  --config="$ROOT/cloudbuild-frontend.yaml" \
  --project="$PROJECT" \
  --substitutions="COMMIT_SHA=${COMMIT}"

if gcloud secrets describe dsp-google-client-id --project="$PROJECT" >/dev/null 2>&1 \
  && gcloud secrets describe dsp-google-client-secret --project="$PROJECT" >/dev/null 2>&1; then
  echo "Mounting Google OAuth secrets on backend…"
  gcloud run services update dsp-ai-indicator \
    --project="$PROJECT" \
    --region="$REGION" \
    --update-secrets=DSP_GOOGLE_CLIENT_ID=dsp-google-client-id:latest,DSP_GOOGLE_CLIENT_SECRET=dsp-google-client-secret:latest \
    --quiet
else
  echo "WARNING: dsp-google-client-id/secret not found — Google button will error until secrets are mounted."
fi

echo "Backend providers:"
curl -sS "https://dsp-ai-indicator-6uxsluxowq-el.a.run.app/api/v1/auth/enterprise/providers"
echo
echo "Frontend login: https://dspaiindicator.com/login"
