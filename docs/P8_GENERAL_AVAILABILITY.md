# P8.0 — General Availability (GA) Certification & Release Freeze

**Date:** 2026-07-29  
**Backend:** `2.0.0` · **Frontend:** `2.0.0` · **API:** `v1.0.0`  
**Channel:** `ga-candidate` (General Availability Candidate)  
**Certification:** `scripts/ops/certify_p8.py`  
**Engineering decision:** **PASS WITH CONDITIONS**  
**Ship posture:** **GO WITH CONDITIONS**

---

## Executive Summary

DSP AI Indicator completes its engineering programme through P7.4 and enters **RELEASE FREEZE** as a **GA Candidate**. Analytical engines, `/api/v1` behaviour, and database schema are unchanged. Remaining gaps are live-environment operational conditions (paging webhooks, secrets manager, restore drill evidence, ACME/DNS), not product-architecture failures.

---

## Platform Overview

Thin-client research platform: browser renders trust-labelled insights from frozen `/api/v1`; scoring, valuation, AI Committee, and recommendations remain server-side under Research Mode defaults.

| Surface | Version |
|---|---|
| `dsp_platform` | **2.0.0** |
| `dsp-web` | **2.0.0** |
| API contract | **v1.0.0** |
| Production images | `dsp-api:2.0.0` · `dsp-web:2.0.0` |

---

## 1. Complete Platform Audit (P1–P7)

| Milestone | Theme | Result | Notes |
|---|---|---|---|
| **P1** | Production deploy, security hardening, monitoring | **PASS WITH CONDITIONS** | Live ACME/DNS conditioned |
| **P2** | Report / explainability / valuation transparency | **PASS** | Docs + surfaces retained |
| **P3** | (programme continuity / platform excellence track) | **PASS WITH CONDITIONS** | Covered via PEP/architecture docs |
| **P4** | Legal & compliance | **PASS** | `P4_1_LEGAL_AND_COMPLIANCE` |
| **P5** | Closed beta + stabilisation | **PASS WITH CONDITIONS** | Beta programme docs live |
| **P6** | Commercial readiness | **PASS WITH CONDITIONS** | Support mailbox / status page conditions |
| **P7.0** | Production infrastructure | **PASS WITH CONDITIONS** | Compose + Caddy + Prometheus |
| **P7.2** | Release engineering | **PASS** | validate/notes/SBOM/certs |
| **P7.3** | Performance | **PASS WITH CONDITIONS** | Offline harness; live load conditioned |
| **P7.4** | Ops / observability / DR | **PASS WITH CONDITIONS** | Webhooks + restore evidence conditioned |
| **P8.0** | GA certification + freeze | **PASS WITH CONDITIONS** | This report |

No milestone audited as **FAIL**. Conditions require a real production environment and must **not** be removed by documentation alone.

---

## 2. Engineering Summary

| Domain | Score (/10) | Notes |
|---|---|---|
| Architecture / trust | 9.0 | Thin client + constitution held |
| Release engineering | 9.0 | Manifests, SBOM, validate_release |
| Performance | 8.1 | P7.3 offline |
| Operations readiness | 7.7 | P7.4 checklist |
| Security (config) | 8.0 | Headers/auth/rate-limit; secrets mgr conditioned |
| Documentation | 9.0 | GA pack + ops/commercial/legal |
| **Overall Engineering Score** | **8.5** | |

---

## 3. Security Summary

| Control | Status |
|---|---|
| Security headers / HSTS | **PASS** (Caddy + API flags) |
| Authentication / admin auth | **PASS** (production defaults) |
| Authorization denials metered | **PASS** |
| HTTPS readiness | **PASS** (config) · live ACME **CONDITION** |
| Rate limiting | **PASS** (enabled; single-worker constraint) |
| Secrets management | **CONDITION** (KMS) |
| Monitoring + alerting rules | **PASS** · live webhooks **CONDITION** |
| Risk register | **PASS** (`PRODUCTION_RISK_REGISTER.md`) |

**Security certification:** **PASS WITH CONDITIONS**

---

## 4. Operations Summary

| Control | Status |
|---|---|
| Deployment / rollback scripts | **PASS** |
| Backup / incremental / restore | **PASS** |
| Runbooks | **PASS** |
| Monitoring dashboard | **PASS** (Grafana provisioned) |
| Logging | **PASS** · SIEM **CONDITION** |
| Alerting rules | **PASS** · paging **CONDITION** |
| Disaster recovery RPO/RTO | **PASS** (≤24h / ≤4h documented) |
| Operational readiness checklist | **PASS WITH CONDITIONS** (7.7/10) |

**Operations certification:** **PASS WITH CONDITIONS**

---

## 5. Documentation Summary

| Pack | Status |
|---|---|
| README + version matrix/history | **PASS** |
| Architecture / constitution / trust | **PASS** |
| Commercial / support / legal | **PASS** |
| Deployment / operations / DR | **PASS** |
| API reference | **PASS** |
| GA architecture / debt / freeze / this report | **PASS** |

**Documentation certification:** **PASS**

---

## 6. Architecture Certification

See `docs/GA_ARCHITECTURE_CERTIFICATION.md` — **PASS WITH CONDITIONS**.

---

## 7. Known Limitations

1. Single-region reference compose (not multi-AZ).  
2. Logical dumps (not PITR) for default RPO.  
3. Cold façade import latency.  
4. No explicit `dsp_active_sessions` Prometheus gauge.  
5. Historical interim version tags superseded by aligned **2.0.0** commercial GA-candidate tag.

---

## 8. Remaining Operational Conditions

1. Wire Alertmanager receivers to on-call (PagerDuty/Slack).  
2. Secrets manager instead of long-lived env files.  
3. Record restore/RTO drill evidence.  
4. Prove ACME/HTTPS on real DNS.  
5. Rotate Grafana admin password; restrict Grafana exposure.  
6. Optional: SIEM, status page, multi-AZ.

These conditions **remain** — they need a real production environment.

---

## 9. Scores

| Score | Value |
|---|---|
| Overall Engineering Score | **8.5 / 10** |
| Overall Production Score | **8.0 / 10** |
| GA Readiness Score | **8.2 / 10** |

---

## 10. Release Freeze

**IN EFFECT** — see `docs/RELEASE_FREEZE.md`.

Engineering must not add features, analytical changes, API behaviour changes, UI redesign, or schema changes. Hotfixes only per freeze policy.

---

## 11. Final Decision

| Gate | Result |
|---|---|
| Platform audit | **PASS WITH CONDITIONS** |
| Architecture | **PASS WITH CONDITIONS** |
| Security | **PASS WITH CONDITIONS** |
| Operations | **PASS WITH CONDITIONS** |
| Documentation | **PASS** |
| Technical debt register | **PASS** |
| Release freeze | **PASS** (document active) |
| `certify_p8.py` | **PASS** |

### Engineering certification

**PASS WITH CONDITIONS**

### Ship posture

**GO WITH CONDITIONS**

Do **not** declare unconditional PASS/GO while live operational conditions remain. GA Candidate is appropriate; unrestricted public GA traffic waits on conditions above.

---

## Certification evidence

`python scripts/ops/certify_p8.py` → **CERTIFICATION_P8 PASS** · **GA_DECISION PASS_WITH_CONDITIONS** (2026-07-29).
