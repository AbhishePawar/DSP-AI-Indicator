# COMMERCIAL LAUNCH CHECKLIST

| Field | Value |
|---|---|
| Programme | Commercial Launch Readiness — Operational Prerequisites |
| Tip | `f1fe788` · branch `cursor/p6-1-commercial-readiness` |
| Probe UTC | 2026-08-04T07:22:07Z |
| Host | Windows 10.0.26200 — no K8s/Docker/cloud CLIs |
| Status legend | **PASS** = live deployed evidence · **PARTIAL** = local/harness only · **FAIL** = executed or probed and failed · **NOT EXECUTED** = blocked / not started |
| Cross-refs | `EXTERNAL_DEPLOYMENT_PREREQUISITES.md` X-01…X-11 · EPIC-019B `COMMERCIAL_GA_CERTIFICATION.md` · `GO_NO_GO_DECISION.md` |

**Rule:** No item marked PASS without real evidence from a deployed environment.

---

## Twelve operational prerequisites

| # | Prerequisite | Status | EPIC-019B / X-ID | Evidence |
|---|---|---|---|---|
| 1 | Provision production Kubernetes cluster | **NOT EXECUTED** | X-03 | `kubectl`/`az`/`aws`/`gcloud` **MISSING**; no kubeconfig; no cluster created |
| 2 | Deploy release candidate | **NOT EXECUTED** | X-03 | Helm/Kustomize/compose artefacts **PRESENT** in git; `helm`/`kubectl`/`docker` **MISSING** — apply never run |
| 3 | Configure managed PostgreSQL with PITR | **NOT EXECUTED** | X-04 | No cloud DB; `DSP_DATABASE_URL` **ABSENT**; `psql` **MISSING** |
| 4 | Configure managed Redis | **NOT EXECUTED** | X-05 | No managed Redis; `DSP_REDIS_URL` **ABSENT**; `redis-cli` **MISSING** |
| 5 | Configure production billing provider | **NOT EXECUTED** | X-01 | `stripe` CLI **MISSING**; billing API keys **ABSENT**; no fake checkout |
| 6 | Configure production IdP with MFA | **NOT EXECUTED** | X-02 | Azure AD / Okta / Google env vars **ABSENT**; no IdP session |
| 7 | Configure production DNS and TLS | **FAIL** / **NOT EXECUTED** | X-10 (+ TLS) | `nslookup` → NXDOMAIN for `*.dsp-ai-indicator.example` / `staging.example`; `openssl` **MISSING**; no cert issued |
| 8 | Execute 24-hour soak test | **NOT EXECUTED** (prior **PARTIAL** harness) | X-06 | No live target; prior EPIC-019A ~3 min TestClient only (`docs/testing/SOAK_TEST_REPORT.md`) — **not** 24h prod |
| 9 | Execute multi-host load testing | **NOT EXECUTED** | X-07 | `k6` **MISSING**; no multi-host target; scripts exist in `scripts/perf/` only |
| 10 | Execute PITR restore drill | **NOT EXECUTED** | X-04 | See `DISASTER_RECOVERY_VALIDATION_REPORT.md` — drill never started |
| 11 | Physical Safari/macOS validation | **NOT EXECUTED** | X-08 | Host is Windows; Safari.app / macOS indicators **False** |
| 12 | Verify production monitoring and alerting | **NOT EXECUTED** | Reinforcing | Alert YAML in git (`deploy/observability/prometheus/production_alerts.yml`); live Prometheus/Alertmanager **not** verified |

---

## Related board items (not in the 12, still blocking GA)

| ID | Item | Status | Evidence |
|---|---|---|---|
| X-09 | Trivy image scan on release tip | **PARTIAL** (process) | CI wired historically; this host has no `trivy` binary; no new scan artefact produced this pass |
| X-10 | Support/sales DNS (non-`.example`) | **FAIL** | Documented `*@dsp-ai-indicator.example`; DNS NXDOMAIN |
| X-11 | Board unlock for unrestricted Commercial GA language | **NOT PASS** | Policy — remains REJECTED pending PASS on commercial criticals |

---

## Aggregate

| Category | Count |
|---|---|
| PASS | **0** |
| PARTIAL | **1** related (X-09 process / prior soak harness cited under item 8 as prior PARTIAL only) |
| FAIL | **1+** (DNS placeholders) |
| NOT EXECUTED | **11** of 12 primary items (item 7 also FAIL on DNS probe) |

**Checklist gate: Commercial Launch NOT APPROVED.**
