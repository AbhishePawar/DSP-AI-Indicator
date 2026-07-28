# compliance

## Purpose

DSP Compliance — Research Mode flags/terminology + **PEP-004** India compliance foundation (DPDP consent, disclosures, history, retention, export).

## Version

**0.2.0**

## Usage

```python
from compliance import ComplianceBundle, FeatureFlags

bundle = ComplianceBundle.create()
assert bundle.flags.research_mode is True
print(bundle.disclosures.list_active(mode="research")[0].title)
```

Optional persistence (duck-typed PEP-002 DatabasePort):

```python
from production_platform import InfrastructureBundle
from compliance import ComplianceBundle

infra = InfrastructureBundle.create_offline()
bundle = ComplianceBundle.create(database=infra.database)
```

## Docs

- [PEP_004_INDIA_COMPLIANCE.md](../../docs/PEP_004_INDIA_COMPLIANCE.md)
- [COMPLIANCE_ARCHITECTURE.md](../../docs/COMPLIANCE_ARCHITECTURE.md)
- [DPDP_ARCHITECTURE.md](../../docs/DPDP_ARCHITECTURE.md)
- [DISCLOSURE_GUIDE.md](../../docs/DISCLOSURE_GUIDE.md)

## Non-goals

SEBI adviser workflows, Aadhaar, PAN, DigiLocker, UPI, engine math.
