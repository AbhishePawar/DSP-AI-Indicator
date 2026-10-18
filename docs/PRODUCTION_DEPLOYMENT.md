# Production Deployment — Infrastructure (PEP-002)

## Mandatory India posture

| Control | Setting |
|---|---|
| Primary region | India (`ap-south-1` / Azure Central India / GCP Mumbai) |
| Timezone default | `Asia/Kolkata` |
| Currency default | `INR` |
| DB | Managed PostgreSQL (India residency) |
| Cache | Managed Redis (same region) |
| Primary artifacts | Persistent VPS local filesystem |
| Off-server backup / overflow | S3 in `ap-south-1`; new objects overflow at 95% local disk use |
| Log retention | ≥180 days (CERT-In) |
| Secrets | Cloud KMS + Secrets Manager behind `SecretsPort` |

## Environment skeleton

```bash
DSP_ENVIRONMENT=production
DSP_REGION=ap-south-1
DSP_DATABASE_URL=postgresql://...
DSP_REDIS_URL=rediss://...
DSP_REDIS_FALLBACK=true
DSP_OBJECT_STORAGE_PROVIDER=local
DSP_OBJECT_STORAGE_LOCAL_ROOT=/var/lib/dsp/artifacts
DSP_BACKUP_S3_BUCKET=<verified-existing-production-bucket>
DSP_BACKUP_S3_REGION=ap-south-1
DSP_STORAGE_OVERFLOW_THRESHOLD=0.95
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

## Off-server backup verification

`DSP_BACKUP_S3_BUCKET` must be an existing bucket with least-privilege permissions for the VPS role. Run `python3 scripts/ops/verify_s3_staging.py --confirm-staging-s3-write` on the staging VPS with `DSP_ENVIRONMENT=staging`, `DSP_BACKUP_S3_BUCKET`, and `DSP_BACKUP_S3_REGION` configured. This performs a temporary object put/get/delete test and verifies cleanup. The application is not considered AWS-connected until this passes using the intended VPS credentials.\n\n## Health\n
- Liveness: process + configuration (no external deps)
- Readiness: ports registered + optional `database.ping()` when infra attached

## Non-goals (this epic)

- Does not change `/api/v1` contracts
- Does not activate SEBI Mode
- Does not implement DigiLocker / PAN / UPI (ports only)
- Does not run Celery/RQ workers yet (`JobQueuePort` architecture ready)
