# production_platform

## 1. Package Purpose

DSP Production Services — provider-neutral ops ports (K1.3)

## 2. Responsibilities

- Provide the `production_platform` domain façade for DSP AI Indicator.
- Expose stable public exports via `__all__`.
- Remain within architecture allowlists (ASI-003).

## 3. Package Status

**Production · Frozen** · Epic K  
Version: **0.1.0**  
Canonical versions → [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

- Package version: `0.1.0`
- `CachePort`
- `ConfigurationError`
- `ConfigurationManager`
- `DiagnosticsManager`
- `DiagnosticsReport`
- `Environment`
- `FeatureFlag`
- `FeatureFlagManager`
- `HealthCheckResult`
- `HealthManager`
- `HealthReport`
- `HealthStatus`
- `InMemoryCachePort`
- `InMemoryLoggingPort`
- `InMemoryMetricsPort`
- `InMemorySchedulerPort`
- `InMemorySecretsPort`
- `InMemoryStoragePort`
- `InMemoryTracingPort`
- `LogRecord`
- `LoggingPort`
- `MetricSample`
- `MetricsPort`
- `ProductionBundle`
- `ProductionConfiguration`
- … and 13 more (see `__all__` in package `__init__.py`)

Import the package root only for public use unless tests intentionally exercise internals.

## 5. Package Structure

```
packages/production_platform/
├── README.md
├── pyproject.toml (if present)
├── src/production_platform/
│   └── …
└── tests/
```

## 6. Dependencies

Declared in `pyproject.toml`:

- `core`

## 7. Architecture Notes

- Feature freeze: do not add product behaviour under ASI documentation tasks.
- Forbidden imports are enforced by `tests/test_architecture.py` where present.
- Thin-client / platform rules → [ARCHITECTURE_GOVERNANCE.md](../../docs/ARCHITECTURE_GOVERNANCE.md).

## 8. Usage Examples

```python
from production_platform import CachePort

# See package tests for worked examples against frozen façades.
_ = CachePort
```

## 9. Testing

```bash
pytest packages/production_platform/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

- Ownership → [PACKAGE_OWNERSHIP_MATRIX.md](../../docs/PACKAGE_OWNERSHIP_MATRIX.md)
- Governance standard → [PACKAGE_GOVERNANCE.md](../../docs/PACKAGE_GOVERNANCE.md)
- ASI framework → [ASI_IMPLEMENTATION_FRAMEWORK.md](../../docs/ASI_IMPLEMENTATION_FRAMEWORK.md)

## 11. Limitations

- Documents **current** implementation only.
- Does not embed upstream report payloads or re-run foreign domain math.
- Not a substitute for epic freeze docs under `docs/`.

## 12. Future Extensions (future only)

Any new analytics, providers, or API shapes require an approved epic and ADR. **Not implemented in this package README.**
