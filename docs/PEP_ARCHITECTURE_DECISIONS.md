# PEP Architecture Decisions (ADR Register)

| Field | Value |
|---|---|
| **Version** | `1.0.0` |
| **Status** | **Active** |
| **Last updated** | 2026-07-28 |
| **Authority** | [PEP_000_ENTERPRISE_ARCHITECTURE_FREEZE.md](PEP_000_ENTERPRISE_ARCHITECTURE_FREEZE.md) |
| **Template** | Status · Context · Decision · Consequences · Alternatives · India notes |

---

## How to use

1. Every material PEP change requires an ADR entry here (or link to `docs/adr/` using [asi/ADR_TEMPLATE.md](asi/ADR_TEMPLATE.md)).
2. ADRs in this file are **platform/enterprise** scoped — they must not alter frozen investment math.
3. Conflicts with [DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md) → STOP → escalate.

---

## ADR-PEP-0001 — Preserve hexagonal ports; adapters only

| Field | Content |
|---|---|
| **Status** | Accepted |
| **Context** | Enterprise needs DB, Redis, OTel, IdP without rewriting engines |
| **Decision** | Implement all PEP capabilities as adapters behind `production_platform`, `security_platform`, `data_engine`, and `compliance` ports |
| **Consequences** | Offline in-memory adapters remain for tests; prod swaps adapters via config |
| **Alternatives** | Embed Redis/SDK calls inside engines — rejected |
| **India** | India-region managed services chosen at adapter config, not domain code |

---

## ADR-PEP-0002 — Security wraps HTTP; domain stays auth-independent

| Field | Content |
|---|---|
| **Status** | Accepted (reaffirmation of DSP Architecture) |
| **Context** | Multi-tenant identity must not leak into valuation packages |
| **Decision** | `dsp_platform` and L1 engines never import `security_platform`; JWT/RBAC enforced at gateway/`api_platform` |
| **Consequences** | `SecurityContext` injected at edge; engines receive only research inputs |
| **Alternatives** | Pass user objects into engines — rejected |
| **India** | Supports DPDP minimization (engines never see Aadhaar/PAN) |

---

## ADR-PEP-0003 — Thin client remains absolute

| Field | Content |
|---|---|
| **Status** | Accepted (EPIC-015) |
| **Context** | Browser engines were removed; must not return |
| **Decision** | All investment calculations execute server-side; web is presentation + API client only; architecture tests enforce |
| **Consequences** | Richer UI needs richer API serialization (additive), not TS engines |
| **Alternatives** | WASM scoring in browser — rejected |
| **India** | Consistent disclosures via Research Mode terminology ports |

---

## ADR-PEP-0004 — PostgreSQL as system of record

| Field | Content |
|---|---|
| **Status** | Accepted |
| **Context** | Ephemeral stores block audit, history, tenancy |
| **Decision** | Managed PostgreSQL in India region for identity, sessions metadata, audit, research history, DPDP records, job state |
| **Consequences** | New schemas owned by Identity / Compliance / Research Lifecycle BCs — not by valuation packages |
| **Alternatives** | Document DB only — rejected for relational audit needs |
| **India** | Data residency in India primary region |

---

## ADR-PEP-0005 — Redis for cache, sessions, distributed rate limits

| Field | Content |
|---|---|
| **Status** | Accepted |
| **Context** | Process-local cache/rate limit fails under horizontal scale |
| **Decision** | Redis for AnalyseResponse cache keys, session secondary data, distributed rate-limit counters |
| **Consequences** | Cache keys include `pipeline_version` + config hash for determinism safety |
| **Alternatives** | Sticky sessions only — rejected |
| **India** | Redis in same region as API |

---

## ADR-PEP-0006 — OIDC as primary enterprise authentication

| Field | Content |
|---|---|
| **Status** | Accepted |
| **Context** | Passwordless RC login unfit for RIA/family office |
| **Decision** | Implement `OAuth2TokenValidator` with OIDC (Keycloak / Azure AD / Google Workspace); MFA required for ADMIN/COMPLIANCE roles |
| **Consequences** | Local password+MFA allowed for small deployments behind flag; passwordless deprecated |
| **Alternatives** | Custom SSO — rejected |
| **India** | Supports org IdPs common to Indian enterprises |

---

## ADR-PEP-0007 — Research Mode default; SEBI Mode gated

| Field | Content |
|---|---|
| **Status** | Accepted (PR1.0 reaffirmation) |
| **Context** | Premature Buy/Sell UI creates regulatory risk |
| **Decision** | Research Mode remains default until explicit SEBI registration epic + flags; PEP never activates SEBI Mode |
| **Consequences** | Recommendation history still stored for research assessments under educational language |
| **Alternatives** | Always-on recommendations — rejected |
| **India** | Aligns with SEBI RA/IA caution |

---

## ADR-PEP-0008 — DPDP as first-class compliance subsystem

| Field | Content |
|---|---|
| **Status** | Accepted |
| **Context** | DPDP Act 2023 applies to personal data of users/clients |
| **Decision** | Introduce DPDP services (consent, purpose, retention, erasure, export) in Compliance BC; minimize PII in research payloads |
| **Consequences** | Engines remain free of personal identifiers; identity BC owns PII |
| **Alternatives** | Ignore until sued — rejected |
| **India** | Mandatory for enterprise readiness score |

---

## ADR-PEP-0009 — CERT-In logging posture

| Field | Content |
|---|---|
| **Status** | Accepted |
| **Context** | CERT-In directions expect synchronized clocks and retained logs |
| **Decision** | Structured logs with ≥180-day retention; NTP; incident runbooks; correlation IDs |
| **Consequences** | Log volume/cost; required for Indian Market Readiness |
| **Alternatives** | Console-only logs — rejected for prod India |
| **India** | Explicit CERT-In alignment |

---

## ADR-PEP-0010 — IST and INR as operational defaults for India deploy

| Field | Content |
|---|---|
| **Status** | Accepted |
| **Context** | Product UTC-centric; users expect IST/INR |
| **Decision** | India deploy profile defaults `Asia/Kolkata` for presentation/exports; INR formatting in reports; engines may keep UTC internally with explicit as-of |
| **Consequences** | Clear conversion boundaries in API mappers |
| **Alternatives** | Force users to convert — rejected |
| **India** | Market holidays via `MarketCalendarPort` |

---

## ADR-PEP-0011 — India market & fintech ports without day-1 implementation

| Field | Content |
|---|---|
| **Status** | Accepted |
| **Context** | NSE/BSE, NSDL/CDSL, DigiLocker, PAN, UPI, OCEN, Account Aggregator are strategic |
| **Decision** | Define ports and threat models in Data/Identity BCs; implement only when licensed epic approved; never store Aadhaar without dedicated legal epic |
| **Consequences** | Prevents premature PII gravity; keeps roadmap honest |
| **Alternatives** | Build integrations now — rejected (scope/legal) |
| **India** | Future-proof architecture |

---

## ADR-PEP-0012 — LLM explains; engines decide

| Field | Content |
|---|---|
| **Status** | Accepted ([AI_PRINCIPLES.md](AI_PRINCIPLES.md)) |
| **Context** | Hallucination risk on financial numbers |
| **Decision** | `llm_adapters` consume grounded engine outputs; safety blocks override language; deterministic fallback required |
| **Consequences** | Prompt registry versioning under PEP; no score mutation |
| **Alternatives** | LLM-generated valuations — rejected |
| **India** | Supports Research Mode educational posture |

---

## ADR-PEP-0013 — Async workers for heavy jobs; sync analyse retained

| Field | Content |
|---|---|
| **Status** | Accepted |
| **Context** | Large exports/reports must not block HTTP |
| **Decision** | Keep interactive `POST /analyse` synchronous; introduce job queue for PDF/bulk/history backfills |
| **Consequences** | New worker service; API gains job status endpoints (additive) |
| **Alternatives** | Make all analyse async — rejected (UX) |
| **India** | Better advisor batch workflows |

---

## ADR-PEP-0014 — Multi-tenancy after identity + DPDP foundations

| Field | Content |
|---|---|
| **Status** | Accepted |
| **Context** | Tenancy without DPDP/identity is unsafe |
| **Decision** | PEP-007 only after PEP-001/002/004 exit criteria; tenant_id in JWT + RLS |
| **Consequences** | Single default tenant initially |
| **Alternatives** | Tenancy first — rejected |
| **India** | Advisor–client isolation for RIAs |

---

## ADR-PEP-0015 — No breaking `/api/v1` without new RC

| Field | Content |
|---|---|
| **Status** | Accepted |
| **Context** | GA API contract trust |
| **Decision** | PEP may add endpoints/fields; breaking changes require new API RC/major |
| **Consequences** | Version matrix discipline |
| **Alternatives** | Silent breaks — rejected |
| **India** | Institutional client stability |

---

## ADR-PEP-0021 — Enterprise composition root (`platform_runtime`)

| Field | Content |
|---|---|
| **Status** | Accepted (PEP-004.1) |
| **Context** | PEP-001…004 bundles must compose without circular BC imports or engine coupling |
| **Decision** | Introduce `platform_runtime` as the offline-capable composition root; consent SoT is `compliance.ConsentPort` behind `ComplianceBackedConsentStore`; do not place composition in engines or thin client |
| **Consequences** | `api_platform` wiring deferred; standalone SecurityBundle may still use local consent for CI |
| **Alternatives** | Import compliance from security — rejected (boundary) |
| **India** | Single DPDP export path for composed deployments |

---

## ADR-CV-001 — Data Authenticity First (core value)

| Field | Content |
|---|---|
| **Status** | Accepted (2026-07-28) |
| **Context** | Risk of placeholder / fabricated market and financial numbers in production research UI and reports |
| **Decision** | Permanent core value **CV-001**: allowed numeric sources only (market, statements, DSP calculated, user, derived); unavailable → “Data unavailable.”; mandatory report header; metric provenance; explainable scores; violation fails architecture review |
| **Consequences** | Quality gates, code review, release, and DoD include CV-001; future report emitters must validate authenticity; no engine/API/scoring changes in this decision |
| **Alternatives** | Soft guideline / example numbers with disclaimer — rejected |
| **India** | Applies in Research Mode and any future SEBI Mode equally |
| **Full ADR** | [adr/ADR-CV-001-data-authenticity-first.md](adr/ADR-CV-001-data-authenticity-first.md) · [CV_001_DATA_AUTHENTICITY_FIRST.md](CV_001_DATA_AUTHENTICITY_FIRST.md) |

---

## ADR-CV-002-010 — Tier-0 Core Values CV-002…CV-010

| Field | Content |
|---|---|
| **Status** | Accepted (2026-07-28) |
| **Context** | Need constitutional constraints beyond authenticity for scoring, explainability, determinism, uncertainty, provenance, audit, research-first, and governance |
| **Decision** | Adopt CV-002…CV-010 as Tier-0 Architecture Governance; any violation fails all enforcement gates |
| **Consequences** | Checklists / DoD / release / production / package health / Cursor rules updated; no engine/API/scoring/model/boundary code changes |
| **Alternatives** | Soft guidelines — rejected |
| **India** | Applies equally in Research Mode and any future SEBI Mode |
| **Full ADR** | [adr/ADR-CV-002-010-tier0-core-values.md](adr/ADR-CV-002-010-tier0-core-values.md) · [CV_002_TO_010_TIER0_CORE_VALUES.md](CV_002_TO_010_TIER0_CORE_VALUES.md) |

---

## ADR-RS-001 — Constitutional Research Standards (RS-001…RS-010)

| Field | Content |
|---|---|
| **Status** | Accepted (2026-07-28) |
| **Context** | CV defines behaviour; reports still need a mandatory minimum content set |
| **Decision** | Adopt RS-001…RS-010 as constitutional report content; missing section fails Research Report Validation |
| **Consequences** | Specs / checklists / gates updated; no engine/API/scoring/model/boundary changes |
| **Alternatives** | Soft optional sections — rejected |
| **India** | Research Mode terminology for Recommendation Status; flags still gate advice labels |
| **Full ADR** | [adr/ADR-RS-001-research-standards.md](adr/ADR-RS-001-research-standards.md) · [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md) |

---

## Pending ADRs (to be filed during implementation)

| ID | Topic | When |
|---|---|---|
| ADR-PEP-0016 | Exact IdP product selection | Still pending at OIDC kickoff; password+MFA foundation shipped in PEP-001 |
| ADR-PEP-0017 | Queue technology selection | **Accepted (foundation):** `JobQueuePort` + in-memory reference; Redis Streams / SQS / RabbitMQ reserved via config — worker epic wires execution |
| ADR-PEP-0018 | Log backend (Loki vs ELK vs cloud) | **Accepted (foundation):** structured JSON + AuditEventPort; collector choice deferred to deploy |
| ADR-PEP-0019 | WORM audit store requirement | PEP-004 legal review |
| ADR-PEP-0020 | K8s timing vs managed containers | Scale trigger |

---

## Related

[PEP_000_ENTERPRISE_ARCHITECTURE_FREEZE.md](PEP_000_ENTERPRISE_ARCHITECTURE_FREEZE.md) · [PEP_DEPENDENCY_RULES.md](PEP_DEPENDENCY_RULES.md) · [DSP_DECISION_RECORDS.md](DSP_DECISION_RECORDS.md)
