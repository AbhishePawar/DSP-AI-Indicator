# GA Technical Debt Register — EPIC-P8.0

**Date:** 2026-07-29  
**Policy:** No new analytical debt under freeze. Ops debt may be deferred with rationale.

| ID | Item | Category | Rationale / Plan | Owner |
|---|---|---|---|---|
| TD-C01 | Alertmanager webhooks still placeholders | **Critical** | Must wire before unrestricted GA traffic; silent paging risk (OPS-03) | Platform Ops |
| TD-C02 | Secrets often file-based (`.env.production`) | **Critical** | Move to KMS/Secrets Manager for enterprise tenants (OPS-07) | Security |
| TD-H01 | No recorded quarterly restore/RTO drill evidence | **High** | Scripts exist; evidence requires live environment (OPS-12) | Platform Ops |
| TD-H02 | Grafana default/admin password hygiene | **High** | Enforce unique `GRAFANA_ADMIN_PASSWORD` at deploy (OPS-11) | Platform Ops |
| TD-H03 | Single-region deployment | **High** | Multi-AZ deferred until revenue justifies; DR docs mitigate (OPS-01) | Platform Ops |
| TD-H04 | ACME/DNS live certification not proven in this repo run | **High** | Requires public domain; P7.0 condition | Platform Ops |
| TD-M01 | Cold import ~13s of `dsp_platform` façade | **Medium** | Accepted for GA; lazy-load only in future non-behaviour epic (OPS-09) | Engineering |
| TD-M02 | In-process rate limits block safe multi-worker | **Medium** | Keep workers=1 until Redis-backed limiter (P7.3) | Engineering |
| TD-M03 | No central SIEM / log aggregation | **Medium** | Local JSON + rotation sufficient for GA-candidate; SIEM per enterprise SKU | Platform Ops |
| TD-M04 | Active session gauge not explicit in Prometheus | **Medium** | Dashboard uses operational proxies; additive metric later without contract break | Engineering |
| TD-M05 | Dependency CVE triage ongoing | **Medium** | `security.yml` workflow; patch cadence (OPS-13) | Security |
| TD-L01 | Historical frontend tags 2.0.1–2.0.4 collapsed to commercial **2.0.0** GA tag | **Low** | Intentional governance alignment; history retained in VERSION_HISTORY | Release Eng |
| TD-L02 | Duplicate/overlapping older deploy docs (P1.1 vs P7) | **Low** | P7 docs authoritative; older retained for audit trail | Docs |
| TD-L03 | cAdvisor privileged mode | **Low** | Accepted; prefer managed metrics later (OPS-10) | Security |
| TD-D01 | Physical WAL / PITR continuous backup | **Deferred** | Logical dumps meet RPO≤24h; PITR when managed Postgres adopted | Platform Ops |
| TD-D02 | Multi-worker horizontal scale | **Deferred** | Blocked on Redis rate-limit design; not required for GA-candidate single-node | Engineering |
| TD-D03 | Browser performance budgets in CI | **Deferred** | P7.3 offline harness exists; Lighthouse CI later | Frontend |
| TD-D04 | Full SBOM via syft/cyclonedx in every CI run | **Deferred** | Anchor SBOM in `release/sbom.json`; deepen when tooling pinned | Release Eng |
| TD-D05 | Status page product | **Deferred** | Commercial condition (P6.1); not engineering blocker for freeze | Support |

## Category counts

| Category | Count |
|---|---|
| Critical | 2 |
| High | 4 |
| Medium | 5 |
| Low | 3 |
| Deferred | 5 |

**Deferred rule:** Deferred items must not block **GA Candidate** certification; Critical items remain **conditions** on unrestricted public GA traffic.
