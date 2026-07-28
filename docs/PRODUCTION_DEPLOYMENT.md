# Production Deployment — Infrastructure (PEP-002)

## Mandatory India posture

| Control | Setting |
|---|---|
| Primary region | India (`ap-south-1` / Azure Central India / GCP Mumbai) |
| Timezone default | `Asia/Kolkata` |
| Currency default | `INR` |
| DB | Managed PostgreSQL (India residency) |
| Cache | Managed Redis (same region) |
| Object storage | S3-compatible in India region |
| Log retention | ≥180 days (CERT-In) |
| Secrets | Cloud KMS + Secrets Manager behind `SecretsPort` |

## Environment skeleton

```bash
DSP_ENVIRONMENT=production
DSP_REGION=ap-south-1
DSP_DATABASE_URL=postgresql://...
DSP_REDIS_URL=rediss://...
DSP_REDIS_FALLBACK=true
DSP_OBJECT_STORAGE_PROVIDER=s3
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
