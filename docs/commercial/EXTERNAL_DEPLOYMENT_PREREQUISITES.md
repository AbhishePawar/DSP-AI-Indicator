# EXTERNAL DEPLOYMENT PREREQUISITES — EPIC-019A

These items require customer/vendor/cloud evidence. **Never mark PASS without artefacts.**

| ID | Prerequisite | Status | Blocks unrestricted Commercial GA? |
|---|---|---|---|
| X-01 | Live billing (Stripe/Razorpay/Paddle) with purchasable packaging | **NOT PASS** — adapters return unavailable | **Yes** (R-001) |
| X-02 | Live IdP SSO/MFA (Azure AD / Okta / Google) | **NOT PASS** — ports/null adapters only | **Yes** (R-002) |
| X-03 | Production Kubernetes cluster deploy + health | **NOT PASS** on validation host | Reinforcing |
| X-04 | Managed Postgres + PITR restore drill | **NOT PASS** | Reinforcing |
| X-05 | Managed Redis (multi-replica rate limit / cache) | **NOT PASS** | Reinforcing |
| X-06 | 8–24h soak on live staging/prod | **NOT PASS** — harness only | Reinforcing (AUD-010) |
| X-07 | Production load (k6 multi-host) | **NOT PASS** | Reinforcing |
| X-08 | Physical Safari.app smoke on macOS | **NOT PASS** — WebKit via Playwright only | Softening of R-004 |
| X-09 | Trivy image scan evidence from CI artefacts on release tip | **CI wired** — local host had no Trivy binary | Process |
| X-10 | Support/sales DNS (non-`.example`) | **NOT PASS** | Reinforcing |
| X-11 | Board unlock for unrestricted Commercial GA language | **NOT PASS** | **Yes** (R-006) |

## Allowed claims

- Version 2.0 **Release Candidate**
- Closed-beta / institutional pilot (Research Mode)
- Engineering packaging / trust / visual / CSP / DevSecOps CI improved (EPIC-019A)

## Forbidden claims

- Generally Available / Commercial GA
- Self-serve checkout readiness
- “Azure AD integrated” / “Stripe live”
- “8–24h production soak certified” without ops JSON evidence
