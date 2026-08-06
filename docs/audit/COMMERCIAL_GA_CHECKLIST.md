# COMMERCIAL GA CHECKLIST — EPIC-018

| Field | Value |
|---|---|
| Product | DSP AI Indicator |
| Version | **2.0.0-rc.1** |
| Question | Ready for **unrestricted Commercial General Availability**? |
| Date | 2026-08-03 |
| Scoring | **PASS** · **PARTIAL** · **FAIL** only |

Checklist is scored for **unrestricted Commercial GA**, not closed-beta pilot readiness.

---

## A. Product & commercial packaging

| # | Item | Result | Evidence |
|---|---|---|---|
| A1 | Purchasable editions / checkout | **FAIL** | Billing adapters unavailable; Null honesty |
| A2 | Entitlement enforcement wired to live billing | **FAIL** | No payment execution / webhooks |
| A3 | Pricing honesty (no theatre) | **PASS** | Illustrative pricing; not sold as live checkout |
| A4 | Support channels production-ready | **PARTIAL** | Runbooks exist; `.example` mailboxes |
| A5 | Legal / disclaimer / Research Mode | **PASS** | P4.1 + Research Mode packaging |

## B. Identity & security

| # | Item | Result | Evidence |
|---|---|---|---|
| B1 | Live enterprise IdP (OIDC/SSO) | **FAIL** | Ports only; Local/Null adapters |
| B2 | MFA available for commercial accounts | **FAIL** | Null MFA architecture |
| B3 | HttpOnly sessions + CSRF | **PASS** | EPIC-016 + tests; packaging review |
| B4 | Security headers (API) | **PASS** | CSP/no-store middleware |
| B5 | Web CSP production-hardened | **PARTIAL** | `unsafe-inline` / `unsafe-eval` residual |
| B6 | Dependency / image scan clean for GA claim | **FAIL** | npm 4 high; trivy/syft unavailable |
| B7 | Secrets not in git; non-root containers | **PASS** | packaging review 13/13 |
| B8 | Rate limiting multi-replica ready | **PARTIAL** | Needs Redis/edge in prod |

## C. Data & durability

| # | Item | Result | Evidence |
|---|---|---|---|
| C1 | Durable enterprise store in production path | **PARTIAL** | DatabaseEnterpriseStore exists; live Postgres not validated |
| C2 | Migrations / rollback validated live | **FAIL** | Not executed on this host |
| C3 | Backup + restore drill evidenced | **FAIL** | Scripts/docs only |
| C4 | Managed PITR for enterprise RPO | **FAIL** | Documented requirement unmet |
| C5 | Redis/session durability posture documented | **PARTIAL** | Architecture docs; live N/A |

## D. Deployment & operations

| # | Item | Result | Evidence |
|---|---|---|---|
| D1 | Production package (Docker/Compose) | **PARTIAL** | Artefacts present; Docker not installed — no live deploy |
| D2 | K8s/Helm manifests valid & operable | **PARTIAL** | 22 YAML + Helm chart; kubectl/helm absent |
| D3 | Health / ready / live validated on live deploy | **FAIL** | Synthetic TestClient only |
| D4 | Rolling / Blue-Green / Canary evidenced | **PARTIAL** | Docs + overlays; dry-run only |
| D5 | Observability (metrics/alerts/OTel) packaged | **PASS** | EPIC-017 observability pack |
| D6 | Incident / rollback / DR runbooks | **PASS** | Ops docs present |
| D7 | On-call / go-live checklist executable | **PARTIAL** | Pilot go-live OK; GA go-live not authorized |

## E. Performance & reliability

| # | Item | Result | Evidence |
|---|---|---|---|
| E1 | Load test at realistic workloads (live) | **FAIL** | Synthetic only; live_cluster=false |
| E2 | P95/P99 within published GA SLOs on staging | **FAIL** | No published field SLOs evidenced |
| E3 | Soak 8–24h | **FAIL** | PARTIAL ~107m synthetic |
| E4 | Field CWV / LHCI published | **FAIL** | OPEN per perf cert |

## F. Quality / UX / trust

| # | Item | Result | Evidence |
|---|---|---|---|
| F1 | Thin client / architecture freeze | **PASS** | No engine redesign in EPIC-016–018 |
| F2 | CV-001 no fabrication on flagship paths | **PASS** | RC2 CRITICAL closed; honesty retained |
| F3 | Universal trust ladder | **FAIL** | AUD-003 OPEN |
| F4 | Headed Visual QA archive | **FAIL** | Unavailable |
| F5 | Chrome / Edge certification | **PASS** | 48/48 live |
| F6 | Firefox physical smoke | **FAIL** | Not installed |
| F7 | Safari physical smoke | **FAIL** | Unavailable on Windows |
| F8 | A11y automation | **PASS** | vitest-axe / CI wired |
| F9 | A11y field (SR / contrast / full-route) | **PARTIAL** | OPEN conditions |
| F10 | No auth/commerce theatre | **PASS** | Closed-beta honesty |

## G. Documentation & release governance

| # | Item | Result | Evidence |
|---|---|---|---|
| G1 | Architecture / API / security docs current | **PASS** | Strong packet; freeze docs |
| G2 | Ops/runbooks complete for pilot | **PASS** | EPIC-017 + release ops |
| G3 | Obsolete docs flagged | **PARTIAL** | Some historical RC1/1.0.0 duplication remains |
| G4 | Release notes honesty (not claiming GA) | **PASS** | RC4 / board explicitly NO-GO GA |
| G5 | Commercial GA board unlock | **FAIL** | Prior REJECTED; CRITICAL open |

---

## Counts

| Result | Count |
|---|---|
| **PASS** | **16** |
| **PARTIAL** | **12** |
| **FAIL** | **17** |
| **Total items** | **45** |

## Checklist decision input

With **17 FAIL** including multiple CRITICAL commercial/security/evidence gates, unrestricted Commercial GA checklist is **not satisfied**.
