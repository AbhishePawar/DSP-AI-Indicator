# P6.1 — Commercial Readiness & Go-To-Market

**Status:** COMPLETE (commercial / ops / docs)  
**Backend:** `dsp_platform` **v1.6.0**  
**Frontend:** `dsp-web` **v2.0.0-rc**  
**API contract:** `v1.0.0-rc1` (unchanged)  
**Decision:** **READY WITH MINOR CONDITIONS**  
**Date:** 2026-07-29  
**Milestone result:** **PASS**

---

## 1. Commercial readiness summary

Non-engineering commercial launch prep is complete: product packaging, pricing policy, onboarding/docs, support model, operational runbooks, and release assets. Analytical engines and frozen analyse contracts were **not** modified.

Living baseline: Backend **1.6.0** · Frontend **2.0.0-rc** · Channel **rc**.

---

## 2. Product packaging

| Edition | Price | Limits (analyses / exports / seats) |
|---|---|---|
| Research | Free | 25 / 10 / 1 |
| Professional | $149/mo · $1,490/yr | 500 / 200 / 5 · 14-day trial |
| Enterprise | Custom | Unlimited* / custom seats · up to 30-day trial |

Details: [commercial/PRODUCT_PACKAGING.md](./commercial/PRODUCT_PACKAGING.md) · UI `/docs/pricing`.  
Beta→prod: [commercial/BETA_TO_PRODUCTION_MIGRATION.md](./commercial/BETA_TO_PRODUCTION_MIGRATION.md).

---

## 3. Pricing & support

- Pricing model, trial, subscription, upgrade/downgrade, refunds: [commercial/PRICING_STRATEGY.md](./commercial/PRICING_STRATEGY.md)
- Support channels, hours, severity, escalation, KB: [commercial/CUSTOMER_SUPPORT.md](./commercial/CUSTOMER_SUPPORT.md) · UI `/docs/support`
- Contacts (placeholder domains for RC): `support@` · `sales@` · `security@` `@dsp-ai-indicator.example`

---

## 4. Customer onboarding

| Asset | Location |
|---|---|
| Welcome / first-run tour | `OnboardingOverlay` + `lib/beta/onboardingSteps.ts` |
| Quick start | `/docs/quick-start` |
| Sample analysis | `/analysis?symbol=AAPL` |
| FAQ | `/docs/faq` |
| User documentation | `/docs/user-guide` + repo user guides |
| Dashboard CTAs | Welcome widget → Quick start / Support |

---

## 5. Operational runbooks

| Runbook | Path |
|---|---|
| Incident response | [ops/runbooks/INCIDENT_RESPONSE.md](./ops/runbooks/INCIDENT_RESPONSE.md) |
| Service outage | [ops/runbooks/SERVICE_OUTAGE.md](./ops/runbooks/SERVICE_OUTAGE.md) |
| Backup recovery | [ops/runbooks/BACKUP_RECOVERY.md](./ops/runbooks/BACKUP_RECOVERY.md) |
| Deployment | [ops/runbooks/DEPLOYMENT.md](./ops/runbooks/DEPLOYMENT.md) |
| Rollback | [ops/runbooks/ROLLBACK.md](./ops/runbooks/ROLLBACK.md) |
| Security incident | [ops/runbooks/SECURITY_INCIDENT.md](./ops/runbooks/SECURITY_INCIDENT.md) |

---

## 6. Release assets

| Asset | Path |
|---|---|
| Release notes | [RELEASE_NOTES_v2.0.0-rc.md](./RELEASE_NOTES_v2.0.0-rc.md) |
| Changelog | [CHANGELOG.md](./CHANGELOG.md) |
| Version history | [VERSION_HISTORY.md](./VERSION_HISTORY.md) |
| Product overview | [PRODUCT_OVERVIEW.md](./PRODUCT_OVERVIEW.md) |
| Launch announcement draft | [LAUNCH_ANNOUNCEMENT_DRAFT.md](./LAUNCH_ANNOUNCEMENT_DRAFT.md) |
| Media kit | [media-kit/README.md](./media-kit/README.md) |

---

## 7. Launch checklist

- [x] Editions + feature matrix documented and presented
- [x] Pricing / trial / refund / upgrade policy documented
- [x] Onboarding tour + quick start + FAQ + sample symbol
- [x] Support model + in-app Support path
- [x] Six operational runbooks published
- [x] Release notes / changelog / overview / launch draft / media kit
- [x] Version alignment Backend 1.6.0 / Frontend 2.0.0-rc
- [x] Commercial readiness scorecard + decision
- [ ] Production DNS for support mailboxes (condition)
- [ ] Durable multi-node invite/programme store (condition from P5.2)
- [ ] ≥5-day live soak evidence attached (condition from P5.2)
- [ ] Edge TLS/HSTS confirmed on public hostname (condition from P5.2)
- [ ] Self-serve billing provider (optional post-RC; operator-assisted OK)

---

## 8. Commercial readiness scorecard

| Dimension | Score (/10) | Grade | Confidence | Rationale |
|---|---|---|---|---|
| Product | 8 | B+ | High | Packaging clear; Research Mode intact; no new analytics needed |
| Operations | 8 | B+ | High | Runbooks + P1.1/P5.2 ops baseline; multi-node invite still a gap |
| Documentation | 9 | A- | High | Commercial suite + in-app docs linked |
| Support | 8 | B+ | Medium | Model defined; mailboxes still `.example` until DNS |
| Compliance | 8 | B+ | High | P4.1 legal surfaces + research-not-advice preserved |
| Security | 8 | B+ | High | P1.2 hardening + fail-closed beta; edge HSTS pending |
| Scalability | 7 | B | Medium | Single-node invite/store limits GA scale |
| **Overall** | **8.0** | **B+** | **High** | Commercial RC viable with minor conditions |

---

## 9. Final commercial decision

### **READY WITH MINOR CONDITIONS**

**Not** unrestricted public GA. Commercial RC may proceed for controlled customers / invitees.

### Remaining commercial blockers (minor)

1. Replace placeholder support/sales/security domains with production mailboxes + DNS.  
2. Durable invite/programme store before multi-replica GA (P5.2 carry-over).  
3. Attach ≥5 consecutive soak days of live cohort evidence.  
4. Confirm edge TLS/HSTS for the public hostname.  
5. (Optional) Wire self-serve billing — not required for operator-assisted Professional/Enterprise.

**Critical blockers:** none for commercial RC.

---

## 10. Testing (P6.1)

| Check | Result |
|---|---|
| Onboarding steps present | PASS |
| Documentation links (pricing/support/quick-start/faq) | PASS |
| Support contact paths | PASS |
| Version consistency 1.6.0 / 2.0.0-rc | PASS |
| Regression / foundation suites | PASS (see CI / local vitest + pytest version asserts) |

---

## Architecture impact

**None** to engines, valuation, recommendation, AI Committee, or analyse API contracts. Presentation, docs, and ops only.

## Components / pages

- `lib/commercial/*` · docs pages under `/docs/{pricing,support,quick-start,faq}`  
- Legal nav Support link · Welcome widget CTAs · onboarding copy  

## Feature flags

No new analytical flags. Closed-beta flags remain operator-controlled.

## Known limitations

Placeholder email domains; media kit screenshots not yet captured; billing self-serve deferred.
