# Kubernetes manifests (EPIC-017)

Architecture freeze — packaging only. No API/engine behaviour changes.

## Layout

```
deploy/k8s/
  base/                 # Namespace, ConfigMap, API, Web, Redis, Postgres, Ingress, HPA, PDB
  overlays/
    staging/
    production/
    canary/
    blue-green/
```

## Apply

```bash
# Preview
kubectl kustomize deploy/k8s/overlays/staging

# Apply staging
kubectl apply -k deploy/k8s/overlays/staging

# Apply production (after secrets exist)
kubectl apply -f deploy/k8s/base/secrets.example.yaml   # replace with vault-synced Secret first
kubectl apply -k deploy/k8s/overlays/production
```

## Secrets

Never commit real `dsp-secrets`. Use External Secrets / Sealed Secrets. See `deploy/docker/secrets.md`.

## Managed services (recommended)

| Component | Prefer |
|---|---|
| Postgres | RDS / Cloud SQL / Azure Database + PITR |
| Redis | ElastiCache / Memorystore / Azure Cache |
| Ingress TLS | cert-manager + Let's Encrypt or cloud LB certs |
| Images | Private registry; scan on push |

## Related

- Helm: `deploy/helm/dsp`
- Compose production: `docker/docker-compose.production.yml`
- Guide: `docs/operations/Production_Deployment_Guide.md`
