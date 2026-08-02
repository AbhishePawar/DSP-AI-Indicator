# Blue-Green deployment (EPIC-017)

## Model

| Colour | Role |
|---|---|
| **Blue** | Current production Service selector (`version=blue`) |
| **Green** | New Deployment with `version=green` |

Traffic switches by updating the Service selector (or Ingress backend) after green passes smoke/health.

## Procedure

1. Deploy green with new image tag; keep blue serving.
2. Wait for green pods Ready; hit green Service directly for smoke:
   ```bash
   kubectl -n dsp port-forward svc/dsp-api-green 18000:8000
   DSP_SMOKE_API_BASE_URL=http://127.0.0.1:18000 python scripts/ops/production_smoke.py
   ```
3. Flip Service selector from `version=blue` → `version=green`.
4. Observe error rate / latency (Grafana) for 15–30 minutes.
5. Scale down blue; retain image tags for rollback (`DSP_PREVIOUS_IMAGE_TAG`).

## Rollback

Flip selector back to blue; or run `./scripts/rollback_production.sh` for Compose.

## Compose analogue

Record previous tags in `.dsp_production_previous_tags`; `rollback_production.sh` restores them.
