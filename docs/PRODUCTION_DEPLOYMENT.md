# Production Deployment — Infrastructure (PEP-002)

## Mandatory India posture

| Control | Setting |
|---|---|
| Primary region | India posture (`DSP_REGION`, timezone `Asia/Kolkata`) |
| Timezone default | `Asia/Kolkata` |
| Currency default | `INR` |
| DB | Neon PostgreSQL via `DSP_DATABASE_URL` (direct host, `sslmode=require`) |
| Cache | In-process memory. Redis is optional and not in the production Compose file |
| Object storage | `memory` unless an S3-compatible bucket is deliberately configured |
| Log retention | ≥180 days (CERT-In) |
| Secrets | Gitignored `.env.production` on the VPS. Not Google Secret Manager |

## Environment skeleton

```bash
DSP_ENVIRONMENT=production
DSP_REGION=ap-south-1
DSP_DATABASE_URL=postgresql://USER:PASSWORD@ep-example.region.aws.neon.tech/dsp?sslmode=require
DSP_OBJECT_STORAGE_PROVIDER=memory
DSP_OBJECT_STORAGE_BUCKET=dsp-prod-artifacts
DSP_OBJECT_STORAGE_REGION=ap-south-1
DSP_CERT_IN_LOG_RETENTION_DAYS=180
DSP_INDIA_TIMEZONE=Asia/Kolkata
DSP_INDIA_CURRENCY=INR
```

Install extras on the API/worker image:

```bash
pip install "production-platform[infra]"
```

Wire once at process start:

```python
from production_platform import InfrastructureBundle, ProductionBundle

infra = InfrastructureBundle.from_environment()
bundle = ProductionBundle.create(
    configuration=infra.configuration.get(),
    infrastructure=infra,
)
```

## Health

- Liveness: process + configuration (no external deps)
- Readiness: ports registered + optional `database.ping()` when infra attached

## Non-goals (this epic)

- Does not change `/api/v1` contracts
- Does not activate SEBI Mode
- Does not implement DigiLocker / PAN / UPI (ports only)
- Does not run Celery/RQ workers yet (`JobQueuePort` architecture ready)
