# Compliance Architecture (PR1.0 + PEP-004)

| Field | Value |
|---|---|
| **Package** | `packages/compliance` **0.2.0** |
| **Authority** | PEP-000 · PEP-001 · PEP-002 · PEP-004 |

---

## Why a bounded context

Product modes, disclosures, DPDP consent, and retention are **cross-cutting**.
They must not leak into valuation / recommendation engines.

```text
Clients / platform_runtime.EnterprisePlatform (PEP-004.1)
        │
        ▼
ComplianceBundle  (CompliancePort)
   ├─ FeatureFlags (Research Mode default)
   ├─ ConsentPort (DPDP)  ← source of truth when composed
   ├─ DisclosurePort + templates (IST/INR)
   ├─ RecommendationHistoryPort
   ├─ ResearchArchivePort
   ├─ AuditPort + AuditRetentionPort
   └─ ComplianceExportPort
        │
        ▼  (optional duck-typed DatabasePort — no production_platform import)
persistence adapters
```

---

## Ports (PEP-004)

| Port | Role |
|---|---|
| `CompliancePort` | Umbrella façade |
| `ConsentPort` | DPDP consent + versioning |
| `DisclosurePort` | Versioned disclosures |
| `RecommendationHistoryPort` | Research assessments / future SEBI history |
| `ResearchArchivePort` | Research artifact retention |
| `AuditRetentionPort` | Immutable audit refs + ≥180d policy |
| `ComplianceExportPort` | Data principal export |

---

## India defaults

- Research Mode **ON**; SEBI Mode **gated**
- Timezone presentation: `Asia/Kolkata`
- Currency presentation: `INR`
- CERT-In retention floor: **180 days**
- No Aadhaar / PAN / DigiLocker / UPI implementations

---

## Non-goals

- SEBI registered adviser workflows  
- Buy/Sell licensing UI  
- Engine math changes  
- OMS  

---

## Related

- [DPDP_ARCHITECTURE.md](DPDP_ARCHITECTURE.md)
- [DISCLOSURE_GUIDE.md](DISCLOSURE_GUIDE.md)
- [PEP_004_INDIA_COMPLIANCE.md](PEP_004_INDIA_COMPLIANCE.md)
