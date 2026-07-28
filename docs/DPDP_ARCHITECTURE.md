# DPDP Architecture (PEP-004 / PEP-004.1)

## Scope

India Digital Personal Data Protection Act, 2023 — **foundation** inside
`compliance` `ConsentPort`. Identity (PEP-001) exposes a thin
`ConsentRecordPort` for auth-adjacent recording.

## Source of truth

| Mode | Consent store |
|---|---|
| **Composed** (`platform_runtime.EnterprisePlatform`) | **`compliance.ConsentPort`** via `ComplianceBackedConsentStore` |
| Standalone `SecurityBundle.create()` | Local in-memory identity store (dev/CI only) |

Do **not** treat identity and compliance as two durable stores in production
composition. Export / retention / purpose catalogs always read compliance.

## Principles

1. **Purpose limitation** — consents keyed by `purpose_id` (identity uses `purpose`; bridge maps fields)
2. **Versioned notices** — `ConsentVersion` with effective date + text
3. **Immutable decisions** — append-only records (grant / withdraw)
4. **Export** — `ComplianceExportPort` for data principal packages
5. **Retention override** — CERT-In audit retention ≥180 days may outlive erasure requests (documented; erasure jobs in later epic)

## Default purposes

| purpose_id | Required |
|---|---|
| `account_administration` | Yes |
| `research_analytics` | No |
| `audit_retention` | Yes |

## Non-goals

- Aadhaar processing  
- PAN verification storage  
- Cross-border transfer automation  

## Composition

```python
from platform_runtime import EnterprisePlatform

platform = EnterprisePlatform.create_offline()
platform.security.identity.record_consent(
    subject_id="usr_1",
    purpose="research_analytics",
    granted=True,
)
export = platform.compliance.exports.export_subject("usr_1")
```

Standalone compliance:

```python
from compliance import ComplianceBundle

bundle = ComplianceBundle.create()
policy = bundle.consents.current_policy()
bundle.consents.withdraw("usr_1", "research_analytics", policy_version=policy.version)
```
