# MASTER AUDIT MATRIX — EPIC-018

| Field | Value |
|---|---|
| Programme | EPIC-018 — Production Validation & Commercial GA Readiness |
| Product | DSP AI Indicator |
| Version under review | **2.0.0-rc.1** (Version 2.0 RC) |
| Branch | `cursor/p6-1-commercial-readiness` |
| Tip at audit start | `389d9b1703e3f1202c83447a900bed14ce27a287` |
| Date | 2026-08-03 |
| Mode | Validation / verification / documentation only — Architecture Freeze |
| Authority | CTO · Principal Architect · Principal SRE · Principal Security · QA Director · Release Manager |

Duplicate findings from RC2/RC3/RC4, GA-005, EPS-002/003, EPIC-011→017, and ops/security packs are **merged** into one ID. Severity reflects **unrestricted Commercial GA** (not closed-beta pilot).

**Status legend:** OPEN · PARTIAL · CLOSED · ACCEPTED_FOR_RC · N/A_ENV  
**Decision legend:** BLOCK_GA · TRACK · ACCEPT_RC · VERIFY_OK

---

## Matrix

| ID | Source | Category | Severity | Evidence | Status | Decision | Resolution | Verification | Commit |
|---|---|---|---|---|---|---|---|---|---|
| AUD-001 | GA-005 GA5-C1 · RC4 RC-03 · EPS-002 | Commercial / Billing | **CRITICAL** | `NullBillingAdapter` / Stripe|Razorpay|Paddle adapters return `is_available()==False`; UI honesty **Billing provider unavailable.**; pricing illustrative (`channelsPublished: false`) | OPEN | BLOCK_GA | No purchasable packaging / self-serve entitlements | Code spot-check `packages/enterprise/.../billing_providers.py` + RC4_KNOWN_LIMITATIONS RC-03 | tip `389d9b1` |
| AUD-002 | GA-005 GA5-C2 · RC4 RC-14 · GA-C1 | Visual QA | **CRITICAL** | `VISUAL_QA_MATRIX.md` / `SCREENSHOT_APPROVAL.md` — headed Desktop/Tablet/Mobile × Light/Dark archive unavailable | OPEN | BLOCK_GA | Headed/CI visual archive required before public GA claim | Package re-read EPIC-018; no new headed archive on this host | prior release docs |
| AUD-003 | GA-005 GA5-C3 · RC4 RC-09 · GA-C3 | Trust | **CRITICAL** | Trust ladder strongest on Company Analysis + Institutional Reports; not universal on Dashboard / Portfolio / Research Workspace / IRD | OPEN | BLOCK_GA | Universal compact trust / Research Mode chrome | Prior GA-005 + RC4; architecture freeze — no UI redesign in EPIC-018 | prior |
| AUD-004 | GA-005 GA5-C4 · Browser cert · GA-C2 | Browser | **CRITICAL** | Chrome/Edge live 48/48 PASS; Firefox binary absent; Safari unavailable on Windows | OPEN | BLOCK_GA | Physical Firefox + Safari smoke on primary paths | `BROWSER_CERTIFICATION.md`; EPIC-018 host confirms no Firefox/Safari runtime | prior + EPIC-018 env probe |
| AUD-005 | GA-005 GA-C5 · RELEASE_BOARD | Commercial policy | **CRITICAL** | Unrestricted Commercial GA / public purchase NOT AUTHORIZED; invite-only pilot only | OPEN | BLOCK_GA | Self-serve entitlements **or** formal invite-only commercial policy (still ≠ unrestricted GA) | `RELEASE_BOARD.md` · `GA_CERTIFICATION_REPORT.md` | prior |
| AUD-006 | EPIC-016 remaining · RC4 RC-05 | Identity / SSO | **CRITICAL** | OAuth2/OIDC/SSO ports + Local/Null adapters; live Okta/Entra/Google IdP not integrated; MFA Null | OPEN | BLOCK_GA | Live IdP + MFA before public commercial identity claim | `EPIC_016_PRODUCTION_SECURITY_REPORT.md`; code ports present | `15cd183` lineage |
| AUD-007 | RC2 CRITICAL (BQ alias) | Trust / CV-001 | CRITICAL→CLOSED | Sibling BQ alias fabrication closed on flagship paths | CLOSED | VERIFY_OK | Aggregator-only presentation + anti-alias tests | RC3 re-verify + GA-005 spot-check | RC3 packet |
| AUD-008 | RC2/RC3 auth theatre | Security / Honesty | CRITICAL→CLOSED | Fake registration/reset/verify theatre removed for closed-beta honesty | CLOSED | VERIFY_OK | Admin-provisioned Request Access honesty | GA-005 §16 | prior |
| AUD-009 | EPS-002 · RC4 RC-04 | Persistence | HIGH→PARTIAL | EPIC-016 added `DatabaseEnterpriseStore` over `DatabasePort`; default/tests still allow InMemory; production Postgres ops not live-validated here | PARTIAL | TRACK | Prefer durable store + managed Postgres in prod wiring | Unit tests PASS; **no live Postgres restore on this host** | `15cd183` |
| AUD-010 | EPIC-017 · P5.2 soak condition | Reliability | **HIGH** | Target 8–24h; EPIC-018 ran PARTIAL synthetic soak ~107 min wall / 432 samples / 0 failures; not multi-node | PARTIAL | TRACK | Full 8–24h live cluster soak | `docs/audit/soak_test_results_epic018.json` · `SOAK_TEST_REPORT.md` | EPIC-018 |
| AUD-011 | EPIC-017 load | Performance | **HIGH** | Synthetic TestClient 100/500/1000 (EPIC-018) + prior 5000; live_cluster=false; P95 multi-second under single-process | PARTIAL | TRACK | Multi-host k6 against staging/prod | `LOAD_TEST_REPORT.md` · JSON artefacts | EPIC-017/018 |
| AUD-012 | EPIC-017 ops | Deployment | **HIGH** | Docker/Compose/K8s/Helm artefacts present; **Docker/kubectl/helm not installed** on validation host — live deploy not executed | PARTIAL | TRACK | Live compose/k8s deploy + health/ready/live smoke | Manifest inventory 22 YAML; BG/canary docs dry-run only | `0a9ff3c` + EPIC-018 |
| AUD-013 | EPIC-016 · CSP residual | Security | HIGH | Next.js CSP allows `unsafe-inline` / `unsafe-eval`; API CSP hardened | OPEN | TRACK | Tighten CSP without redesigning app runtime (follow-up) | Security guides + packaging review | prior |
| AUD-014 | npm audit EPIC-018 | Dependencies | HIGH | 4 high (brace-expansion, postcss via next, sharp); 0 critical; force-fix would break Next | OPEN | TRACK | Track upstream Next/sharp; no force downgrade under freeze | `npm audit` 2026-08-03 | EPIC-018 |
| AUD-015 | EPIC-017 SBOM | Supply chain | MEDIUM | Lite SBOM generated; syft/CycloneDX CLI absent; trivy absent | PARTIAL | TRACK | Install syft/trivy in CI | `generate_sbom.py` ok; tools missing | EPIC-017/018 |
| AUD-016 | GA5-H1 · Perf cert | Performance field | HIGH | Field LHCI / CWV unpublished | OPEN | TRACK | Publish field CWV on stable URL | `PERFORMANCE_CERTIFICATION.md` | prior |
| AUD-017 | GA5-H2 · A11y | Accessibility | HIGH | vitest-axe automation PASS; full-route headed axe / contrast / SR smoke open | PARTIAL | TRACK | Field a11y evidence | `ACCESSIBILITY_CERTIFICATION.md` | prior |
| AUD-018 | EPIC-016 actor header | Security | HIGH | Enterprise `X-User-Id` spoofable without JWT-subject binding | OPEN | TRACK | Bind enterprise actor to JWT subject | EPIC-016 remaining risks | prior |
| AUD-019 | EPIC-017 queue | Ops | MEDIUM | Job queue still InMemory until dedicated worker epic | OPEN | ACCEPT_RC | Documented limitation | EPIC_017_COMPLETION_REPORT | prior |
| AUD-020 | EPIC-017 Postgres | DR | HIGH | In-cluster Postgres reference; managed PITR required for enterprise RPO | OPEN | TRACK | Managed Postgres + PITR evidence | DR docs present; live PITR not run | prior |
| AUD-021 | RC4 RC-06 | Collaboration | MEDIUM | Collaboration architecture only — no realtime transport | ACCEPTED_FOR_RC | ACCEPT_RC | Out of GA scope for research product core | RC4 | prior |
| AUD-022 | RC4 RC-12/13 | Security residual | MEDIUM | CSP practical residuals + npm advisories accepted at RC | OPEN | TRACK | Same as AUD-013/014 | RC4 | prior |
| AUD-023 | GA-C6 stale AAPL test | QA hygiene | LOW | Stale commercial onboarding AAPL assertion | CLOSED | VERIFY_OK | Addressed in EPS-003 / RC test hygiene | RELEASE_BOARD addendum | EPS-003 |
| AUD-024 | Silent demo tickers | Trust | CRITICAL→CLOSED | No silent `AAPL` defaults in `apps/web/src` (GA-005 probe) | CLOSED | VERIFY_OK | Removed | GA-005 spot-check | prior |
| AUD-025 | Thin client boundary | Architecture | — | No browser valuation/recommendation; `/api/v1` only | CLOSED | VERIFY_OK | Freeze honored through EPIC-016/017/018 | Architecture reviews | prior |
| AUD-026 | HttpOnly / CSRF | Security | — | Cookie sessions + CSRF double-submit + security middleware (EPIC-016) | CLOSED | VERIFY_OK | Unit/integration tests + packaging review 13/13 | `cookies.py` · csrf middleware · EPIC-018 packaging re-run | `15cd183` |
| AUD-027 | Security packaging | Security / Containers | — | Non-root USER, HEALTHCHECK, k8s drop ALL, no hardcoded secrets | CLOSED | VERIFY_OK | `security_packaging_review.py` **13/13 PASS** (2026-08-03) | EPIC-018 re-run | EPIC-017/018 |
| AUD-028 | EPIC-017 validate | Ops packaging | — | Deploy/ops artefact validation | CLOSED | VERIFY_OK | `validate_epic017.py` **25/25 PASS** | EPIC-018 re-run | EPIC-017/018 |
| AUD-029 | Rate limiting | Security | MEDIUM | In-memory limiter default; DistributedRateLimiter needs Redis in prod | PARTIAL | TRACK | Redis-backed limits in multi-replica | code + PRODUCTION_SECURITY_GUIDE | prior |
| AUD-030 | Support DNS | Commercial ops | MEDIUM | Placeholder `@dsp-ai-indicator.example` mailboxes | OPEN | TRACK | Production DNS for support/sales/security | P6.1 checklist | prior |
| AUD-031 | Blue-Green / Canary | Release eng | MEDIUM | Manifests + README procedures present; **not executed live** | PARTIAL | TRACK | Execute in cluster | `deploy/k8s/overlays/{blue-green,canary}` dry-run inventory | EPIC-017/018 |
| AUD-032 | Backup/restore scripts | DR | MEDIUM | Scripts + docs exist; live restore not executed (no Docker/Postgres here) | PARTIAL | TRACK | Execute restore drill | `docs/ops/BACKUP_AND_RECOVERY.md` · scripts/ops/* | prior |
| AUD-033 | Documentation density | Docs | LOW | High completeness; some historical duplication / obsolete RC1 messaging | PARTIAL | TRACK | Flag obsolete paths in EPIC-018 Doc QA | `DOCUMENTATION_AUDIT.md` + H review | EPIC-018 |
| AUD-034 | GA-C7 board sign-off | Governance | CRITICAL | Product/governance sign-off for broader release absent | OPEN | BLOCK_GA | Re-hearing only after CRITICAL closure | This Release Board | EPIC-018 |

---

## Severity roll-up (Commercial GA lens)

| Severity | OPEN / PARTIAL blockers | CLOSED / ACCEPT_RC |
|---|---|---|
| CRITICAL | AUD-001,002,003,004,005,006,034 (and PARTIAL none at CRITICAL) | AUD-007,008,024 |
| HIGH | AUD-010,011,012,013,014,016,017,018,020 | — |
| MEDIUM / LOW | AUD-015,019,021,022,029–033 | AUD-023,025–028 |

**Rule applied:** Any CRITICAL commercial blocker OPEN ⇒ Commercial GA cannot be approved.

---

## Sources consulted

- `docs/releases/GA_CERTIFICATION_REPORT.md` (GA-005 REJECTED)
- `docs/releases/RELEASE_BOARD.md` · RC3/RC4 packet · `RC4_KNOWN_LIMITATIONS.md`
- `docs/reviews/EPIC_016_PRODUCTION_SECURITY_REPORT.md`
- `docs/operations/EPIC_017_COMPLETION_REPORT.md` · load JSON · validation JSON
- `docs/security/EPIC017_SECURITY_PACKAGING_REPORT.md`
- `docs/P6_1_COMMERCIAL_READINESS.md` · EPS / EPIC-011→015 reviews
- EPIC-018 live probes: tooling availability, validate/security/sbom, npm audit, synthetic load/soak, manifest inventory
