# platform_runtime

## Purpose

DSP enterprise composition root — wires PEP-001…004 bundles without investment
engines or API contract changes (**PEP-004.1**).

## Version

**0.1.0**

## Usage

```python
from platform_runtime import EnterprisePlatform

platform = EnterprisePlatform.create_offline()
assert platform.validate_startup().ok
assert platform.readiness().ready

# Consent SoT = compliance.ConsentPort
platform.security.identity.record_consent(
    subject_id="usr_admin",
    purpose="research_analytics",
    granted=True,
)
```

## Docs

- [PEP_004_1_PLATFORM_INTEGRATION_READINESS.md](../../docs/PEP_004_1_PLATFORM_INTEGRATION_READINESS.md)
- [DPDP_ARCHITECTURE.md](../../docs/DPDP_ARCHITECTURE.md)

## Tests

```bash
pytest packages/platform_runtime/tests -q --import-mode=importlib -p no:cov
```
