# Helm chart — dsp (EPIC-017)

```bash
# Staging
helm upgrade --install dsp-staging deploy/helm/dsp \
  -f deploy/helm/dsp/values-staging.yaml \
  --set existingSecret=dsp-secrets

# Production (managed DB/Redis recommended)
helm upgrade --install dsp deploy/helm/dsp \
  -f deploy/helm/dsp/values-production.yaml \
  --set existingSecret=dsp-secrets
```

Create `dsp-secrets` before install. See `deploy/docker/secrets.md`.
