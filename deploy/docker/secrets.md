# Secrets abstraction (EPIC-017)

**Never bake secrets into images or commit `.env.production`.**

## Required secrets

| Secret | Env / key | Consumer |
|---|---|---|
| JWT signing | `DSP_JWT_SECRET` | API |
| Admin seed | `DSP_SEED_ADMIN_PASSWORD` | API bootstrap |
| Postgres password | `POSTGRES_PASSWORD` / embedded in `DSP_DATABASE_URL` | Postgres + API |
| Grafana admin | `GRAFANA_ADMIN_PASSWORD` | Grafana |
| LLM keys (optional) | `OPENAI_API_KEY`, etc. | API only |
| Razorpay (optional) | `DSP_RAZORPAY_KEY_ID`, `DSP_RAZORPAY_KEY_SECRET`, `DSP_RAZORPAY_WEBHOOK_SECRET` | API only — webhook is `POST /api/v1/saas/webhooks/razorpay` on this host. Do not register that URL in the Razorpay Dashboard until the API is on our HTTPS origin and externally tested. |
| Object storage | provider-specific | API |

## Injection patterns

### Docker Compose

- Load via `env_file: .env.production` (gitignored).
- Prefer Docker secrets / swarm secrets or a mounted file from a secret manager for long-lived clusters.

### Kubernetes

1. **External Secrets Operator** → sync from the operator's secret store (file, Docker secrets, AWS/Azure/GCP if already in use) into `Secret` objects. **GCP Secret Manager is not required for Razorpay.** Independent VPS deployments may inject via gitignored `.env` / Docker `env_file`.
2. **Sealed Secrets** / SOPS for GitOps.
3. Mount as envFrom or volume; never put values in ConfigMaps.

Example (values only in cluster, not git):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: dsp-secrets
  namespace: dsp
type: Opaque
stringData:
  DSP_JWT_SECRET: "<from-vault>"
  DSP_SEED_ADMIN_PASSWORD: "<from-vault>"
  POSTGRES_PASSWORD: "<from-vault>"
  DSP_DATABASE_URL: "postgresql://dsp:<from-vault>@postgres:5432/dsp"
  GRAFANA_ADMIN_PASSWORD: "<from-vault>"
```

Non-secret config → ConfigMap (`deploy/k8s/base/configmap.yaml`).

## Rotation

1. Generate new secret in vault.
2. Roll API pods (or compose recreate) after ConfigMap/Secret update.
3. Invalidate sessions if JWT secret rotated (`DSP_JWT_SECRET` change forces re-auth).
4. Record rotation in incident / change log.
