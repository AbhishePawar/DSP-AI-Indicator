# Configuration Guide (PEP-002)

Typed configuration lives in `production_platform.ProductionConfiguration`.
Load from environment via `load_configuration_from_environ()`.

## Profiles

| `DSP_ENVIRONMENT` | Meaning |
|---|---|
| `development` | Local defaults; in-memory OK |
| `test` | CI / contract tests |
| `staging` | India staging with Postgres/Redis |
| `production` | Non-local `DSP_REGION` required |

## Core variables

| Variable | Purpose | Default |
|---|---|---|
| `DSP_ENVIRONMENT` | Profile | `development` |
| `DSP_SERVICE_NAME` | Service identity | `dsp-ai-indicator` |
| `DSP_SERVICE_VERSION` | Service version | `0.2.0` |
| `DSP_REGION` | Deploy region | `local` (prod → e.g. `ap-south-1`) |
| `DSP_LOG_LEVEL` | Log level | `INFO` |
| `DSP_DATABASE_URL` | Postgres DSN | unset → memory |
| `DSP_REDIS_URL` | Redis URL | unset → memory |
| `DSP_REDIS_FALLBACK` | Degrade to memory if Redis down | `true` |
| `DSP_OBJECT_STORAGE_PROVIDER` | `memory` \| `local` \| `s3` \| `minio` \| `azure` \| `gcs` | `memory` |
| `DSP_OBJECT_STORAGE_BUCKET` | Bucket name | — |
| `DSP_OBJECT_STORAGE_ENDPOINT` | MinIO / custom endpoint | — |
| `DSP_OBJECT_STORAGE_LOCAL_ROOT` | Local FS root | — |
| `DSP_JOB_QUEUE_BACKEND` | `memory` (others reserved) | `memory` |
| `DSP_INDIA_TIMEZONE` | Presentation TZ | `Asia/Kolkata` |
| `DSP_INDIA_CURRENCY` | Presentation currency | `INR` |
| `DSP_CERT_IN_LOG_RETENTION_DAYS` | Must be ≥180 | `180` |

## Secrets

`EnvSecretsPort` reads `DSP_SECRET_<NAME>` (never logged).

Future secret managers (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault)
implement the same `SecretProviderPort` / `SecretsPort` protocol.

## Validation

```python
from production_platform import ConfigurationManager, load_configuration_from_environ

cfg = load_configuration_from_environ()
ConfigurationManager(cfg).validate()
```

Production profile rejects `region=local`.
