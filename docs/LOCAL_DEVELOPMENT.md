# Local Development — Infrastructure (PEP-002)

## Default (no external services)

```bash
pip install -e packages/production_platform
pytest packages/production_platform/tests -q --import-mode=importlib -p no:cov
```

`InfrastructureBundle.create_offline()` and unset `DSP_DATABASE_URL` / `DSP_REDIS_URL`
use in-memory reference adapters. Full monorepo tests stay offline-capable.

## Optional infra profile

```bash
docker compose --profile infra up postgres redis
```

Then:

```bash
pip install -e "packages/production_platform[infra]"
set DSP_DATABASE_URL=postgresql://dsp:dsp@127.0.0.1:5432/dsp
set DSP_REDIS_URL=redis://127.0.0.1:6379/0
```

Composition root selects Postgres/Redis when reachable; otherwise notes degradation
and continues with memory adapters when `DSP_REDIS_FALLBACK=true`.

## Smoke

```python
from production_platform import InfrastructureBundle, ProductionBundle

infra = InfrastructureBundle.create_offline()
assert infra.database.ping()
assert infra.india.timezone == "Asia/Kolkata"

bundle = ProductionBundle.create(with_infrastructure=True)
assert bundle.health().ready
```

## Do not

- Import `psycopg` / `redis` / `boto3` from engines or `dsp_platform`
- Construct vendor clients outside `InfrastructureBundle`
