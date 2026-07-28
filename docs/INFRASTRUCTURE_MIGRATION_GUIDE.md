# Infrastructure Migration Guide (PEP-002)

## From K1.3 in-memory-only ops

1. Upgrade `production_platform` to **0.2.0**.
2. Keep existing `ProductionBundle.create()` callers — **backward compatible**.
3. Opt into infrastructure:

```python
bundle = ProductionBundle.create(with_infrastructure=True)
# or
infra = InfrastructureBundle.from_environment()
bundle = ProductionBundle.create(infrastructure=infra)
```

4. Introduce Postgres schema via `MigrationRunner` in Identity / Compliance / Research Lifecycle BCs — **not** inside valuation packages.
5. Point staging at managed Postgres + Redis; leave engines untouched.

## Schema ownership

| Concern | Owner BC | Must not live in |
|---|---|---|
| Identity / sessions metadata | Identity / security | `valuation`, `financial` |
| Audit / CERT-In indices | Compliance | Engines |
| Research history | Research Lifecycle | Engines |
| Job state | Ops / workers | Engines |

## Rollback

Unset `DSP_DATABASE_URL` / `DSP_REDIS_URL` → composition root falls back to reference adapters. No engine code changes required.
