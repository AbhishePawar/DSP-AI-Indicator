# PEP Dependency Rules

| Field | Value |
|---|---|
| **Version** | `1.0.0` |
| **Status** | **FROZEN** |
| **Last updated** | 2026-07-28 |
| **Authority** | [PEP_000_ENTERPRISE_ARCHITECTURE_FREEZE.md](PEP_000_ENTERPRISE_ARCHITECTURE_FREEZE.md) |
| **Companion** | [DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md) · [dsp_platform.boundaries](../packages/dsp_platform/src/dsp_platform/boundaries.py) |

---

## 1. Purpose

These rules govern **all Platform Excellence implementations** so enterprise adapters cannot corrupt hexagonal boundaries, thin client, or frozen investment logic.

---

## 2. Layer dependency direction (mandatory)

```text
L7 Presentation (apps/web)
    → may call → L6/L5 HTTP only (/api/v1)
L5 api_platform
    → may call → security_platform, dsp_platform, compliance (façades), llm_adapters (façade), production_platform ports
L4 production_platform adapters
    → may call → external infra SDKs (DB, Redis, KMS, OTel) AT ADAPTER EDGE ONLY
L3 dsp_platform / orchestration / compliance
    → may call → L2/L1/L0 public façades
L2 Intelligence packages
    → may call → L1/L0 façades (per existing stack order)
L1 Analysis engines ★ FROZEN
    → may call → L0 only (contracts, core, snapshot inputs)
L0 Foundation
    → leaf / ports only
```

**Nothing may depend upward** against this order.

---

## 3. Forbidden dependencies

| From | Must not import | Why |
|---|---|---|
| Any L1 engine | `api_platform`, `security_platform`, `apps.web`, DB/Redis/LLM SDKs | Hexagonal purity |
| `dsp_platform` | `security_platform` | Auth-independent composition |
| `apps/web` | Any Python package; any local `*Engine`/`*Scoring` | Thin client |
| `llm_adapters` | `valuation`, `investment_recommendation`, `investment_committee`, scoring modules | AI must not own decisions |
| `compliance` | Valuation/recommendation math modules | Policy ≠ scoring |
| New PEP packages | Deep imports of private engine modules | Façade only |
| Identity/DPDP services | L1 engines | PII isolation |
| `compliance` | `security_platform`, `production_platform` | Keep BCs independent; compose in `platform_runtime` |
| `security_platform` | `compliance` | Consent injected via duck-typed port at composition |
| `platform_runtime` | L1 engines, `api_platform`, `apps.web` | Composition only; no HTTP/UI |

---

## 4. Allowed enterprise package placements

| Concern | Allowed home | Forbidden home |
|---|---|---|
| OIDC / RBAC / sessions | `security_platform` adapters | `valuation`, `financial` |
| Postgres repositories | New modules under Identity / Research Lifecycle / Compliance BCs or `production_platform` adapters | Inside L1 engine packages |
| Redis cache | `production_platform` CachePort adapter | Engines |
| OTel / log shipper | `production_platform` logging/tracing/metrics adapters | Engines |
| NSE/BSE adapters | `data_engine` adapters | Engines / web |
| DigiLocker / PAN / UPI / AA / OCEN / demat | Edge ports in Identity or Data BC | Engines; must not ship without legal epic |
| DPDP consent store | Compliance BC (`compliance.ConsentPort`); identity may adapt via composition bridge | Engines |
| Enterprise composition root | `platform_runtime` (PEP-004.1) | Engines; `apps/web` |
| Prompt registry | `llm_adapters` or dedicated ops module | Engines |
| Report PDF workers | Reporting BC + workers calling `dsp_platform` | Reimplement scoring in worker |

---

## 5. Application import rule (unchanged)

External applications and scripts may import only:

- `dsp_platform`
- `contracts`

Web applications may use only HTTP clients to `/api/v1`.

Enforced by `FORBIDDEN_APPLICATION_PACKAGES` / Vitest thin-client tests.

---

## 6. Public façade rule

Cross-package imports must use package `__init__` public API (or documented shared-kernel prefixes). Deep imports (`pkg.internal…`) are forbidden between platform packages.

PEP implementations adding repositories must expose façades; engines remain callers of ports, not ORM models.

---

## 7. Feature-flag dependency rule

| Flag family | May affect | Must not affect |
|---|---|---|
| Research / SEBI / Recommendation | Presentation terminology, disclosure surfaces, history labeling | Numeric engine outputs |
| PEP infra flags (`durable_store`, `oidc`, …) | Adapter selection | Scoring formulas |
| Tenancy flags | Row filters, entitlements | Engine math |

---

## 8. Data flow ownership

```text
Provider SDK  → data_engine adapter → normalized contracts
                                     → snapshot_bridge
                                     → ★ engine
                                     → intelligence artifacts
                                     → api_platform DTO
                                     → thin client view-model
```

No reverse arrows carrying calculated investment values from UI to engines except as **user-supplied assumptions** explicitly typed in request DTOs.

---

## 9. Secrets & config dependency rule

| Config type | Location |
|---|---|
| Engine parameters | Versioned configs / request DTOs — not env sprawl |
| Infra secrets | KMS / Secrets Manager via SecretsPort |
| Feature flags | `compliance` + env bootstrap |
| India profile (IST/INR/region) | Deploy profile / env — not hardcoded in engines |

---

## 10. Test dependency rule

| Test type | May use |
|---|---|
| Engine unit/integration | In-memory / fixtures — **no** network/DB required |
| Architecture / boundary | Static import graphs |
| PEP adapter tests | Testcontainers or ephemeral Postgres/Redis in CI (optional) |
| Web Vitest | Mappers + UI — **no** scoring engines |

Breaking offline engine GREEN to force cloud deps is a **PEP violation**.

---

## 11. Violation response

1. Detect via architecture tests / review  
2. **STOP** merge  
3. File ADR if intentional exception  
4. Otherwise refactor to port/adapter  

---

## Related

[PEP_000_ENTERPRISE_ARCHITECTURE_FREEZE.md](PEP_000_ENTERPRISE_ARCHITECTURE_FREEZE.md) · [PEP_ARCHITECTURE_DECISIONS.md](PEP_ARCHITECTURE_DECISIONS.md) · [DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md)
