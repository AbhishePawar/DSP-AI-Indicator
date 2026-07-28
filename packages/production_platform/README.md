# production_platform

## Purpose

Provider-neutral ops ports — **K1.3 + PEP-002 + PEP-003**.

## Version

**0.3.0**

## Capabilities

- Infrastructure: DB / Redis / storage / jobs (PEP-002)
- Observability: JSON logs, correlation IDs, Prometheus text, OTel-ready tracing, audit pipeline, HealthPort (PEP-003)

## Usage

```python
from production_platform import ProductionBundle, ObservabilityBundle

bundle = ProductionBundle.create(with_infrastructure=True, with_observability=True)
assert bundle.health().ready
print(bundle.render_prometheus())
```

## Optional extras

```bash
pip install "production-platform[infra]"
pip install "production-platform[observability]"
```

## Docs

- [PEP_002_ENTERPRISE_INFRASTRUCTURE_FOUNDATION.md](../../docs/PEP_002_ENTERPRISE_INFRASTRUCTURE_FOUNDATION.md)
- [PEP_003_ENTERPRISE_OBSERVABILITY.md](../../docs/PEP_003_ENTERPRISE_OBSERVABILITY.md)
- [OBSERVABILITY_ARCHITECTURE.md](../../docs/OBSERVABILITY_ARCHITECTURE.md)
- [INFRASTRUCTURE_ARCHITECTURE.md](../../docs/INFRASTRUCTURE_ARCHITECTURE.md)
