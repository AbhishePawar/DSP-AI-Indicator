# Independent backend hosting overlay

This overlay runs the API and web containers on any Kubernetes-compatible host without Cloud Run or Cloud Build. It removes the in-cluster Postgres and Redis workloads and reads their connection values from externally managed Kubernetes resources.

## Configure

1. Copy `external-config.example.yaml` into your secret-management workflow.
2. Replace the example hosts, database URL, Redis URL, and JWT secret.
3. Publish `dsp-external-config` and `dsp-external-secrets` in the `dsp` namespace.
4. Set the image references in `api-patch.yaml` and `web-patch.yaml` to the registry used by the target host.
5. Update the TLS secret and ingress hostnames in `ingress-patch.yaml`.

## Apply

```sh
kubectl apply -k deploy/k8s/overlays/independent
kubectl -n dsp rollout status deployment/dsp-api
kubectl -n dsp rollout status deployment/dsp-web
```

The API readiness endpoint is `/health/ready`; liveness is `/health/live`. Google OAuth and Gemini configuration remain application concerns and are not removed by this hosting overlay.
