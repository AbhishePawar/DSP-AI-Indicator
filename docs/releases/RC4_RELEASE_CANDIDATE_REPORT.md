# RC4 — Version 2.0 Release Candidate Report (EPS-003)

| Field | Value |
|---|---|
| Programme | EPS-003 — Version 2.0 Release Candidate Hardening |
| Product | DSP AI Indicator |
| Version | **2.0.0-rc.1** (`VERSION`) |
| Branch | `cursor/p6-1-commercial-readiness` |
| Tip at start | `5a64ee8` (*feat(platform): implement enterprise commercial platform* · EPS-002) |
| Date | 2026-08-02 |
| Mode | **Feature freeze** — engineering excellence, ops maturity, docs sync; **no** new product features / engines / UX redesign |
| Prior authorities | RC3 PASS WITH CONDITIONS (pilot) · GA-005 **COMMERCIAL GA REJECTED** · EPS-002 enterprise foundation |
| Decision | **RELEASE CANDIDATE** — ready for final independent audit / deployment planning |

---

## 1. Executive Summary

Version **2.0.0-rc.1** transitions the feature-complete Enterprise Research OS (plus EPS-002 enterprise commercial foundation) into a **production-grade Release Candidate** posture.

This programme **did not** add analytical engines, redesign UX, or unlock Commercial GA. It synchronized version metadata, applied conservative security/env hygiene, fixed a stale onboarding test residual (GA-C6), documented architecture freeze and technical debt honestly, and re-ran feasible quality suites.

**RC authorization:** independent audit, staging/pilot deployment planning, and release-board review under Research Mode / institutional pilot constraints.

**RC does not authorize:** unrestricted Commercial public GA, purchasable self-serve checkout, or marketing language that implies billing/SSO/durable enterprise store are production-complete.

Honest commercial posture remains **conditional** — see §11.

---

## 2. Architecture Review

| Area | RC assessment |
|---|---|
| Thin client `/api/v1` | **Preserved** — no browser valuation / recommendation / AI reasoning |
| Research engines (Valuation, BQ, Management, Moat, Risk, AI Committee, Explainability, RI, Comparison, Portfolio) | **Untouched** (behaviour freeze) |
| REP-002 / Trust / GOV-001 | **Preserved** — honesty strings and ontology presentation not redesigned |
| Enterprise foundation (EPS-002) | **In scope as shipped** — Null billing, in-memory store, collaboration ports-only |
| Dead code / duplicates | **Documented** — conservative; no risky mass deletes (see [`RC4_ARCHITECTURE_FREEZE.md`](./RC4_ARCHITECTURE_FREEZE.md)) |
| Feature flags | Enterprise + Research Mode flags retained; no temporary “hack” flags removed without evidence |

**Architecture freeze:** Feature and engine freeze held. Removals limited to documentation of candidates; applied cleanups were version/metadata/security hygiene only.

---

## 3. Performance

| Signal | Evidence | Verdict |
|---|---|---|
| Route splitting | Flagship routes use `next/dynamic` (Analysis, Portfolio, Research, IRD, Portal, Ops, Settings, …) | **PASS** (existing GA-003 posture retained) |
| Package import optimization | `experimental.optimizePackageImports: ["lucide-react"]` | **PASS** |
| Bundle analyzer / budgets | Scripts `npm run analyze` / `perf:budget` present (GA-003) | Tooling **PASS**; field LHCI unpublished |
| Automation suite | `npm run test:quality` → a11y + performance automation **30/30 PASS** | **PASS** |
| Field CWV / LHCI on prod URL | Still unpublished (GA-C4) | **OPEN** — does not block RC; blocks Commercial GA |

No experimental rendering rewrites. No virtualization programme in this epic.

---

## 4. Security

| Topic | Finding | Action |
|---|---|---|
| Secrets in client | `NEXT_PUBLIC_*` used for non-secrets only; LLM keys server-side in templates | Documented; `.env.example` hygiene updated |
| JWT / admin passwords | Production template requires `CHANGE_ME_*` + secret manager guidance | Retained |
| CSP (web) | Enforced CSP; added `object-src 'none'` (EPS-003) | Safe hardening applied |
| API headers | nosniff / frame deny / referrer / permissions / DNS prefetch; added `X-Permitted-Cross-Domain-Policies: none` | Safe hardening applied |
| CSRF / HttpOnly cookies | Browser token storage still open (P1.2 residual); enterprise actor via `X-User-Id` foundation | **Documented — not fake-fixed** |
| RBAC | Enterprise permission keys + institutional admin wiring (EPS-002) | Foundation **PASS WITH CONDITIONS** |
| npm audit | 4 high via Next-bundled `postcss` / `sharp`; `npm audit fix --force` would break Next | **Documented — no breaking force upgrade** |
| XSS | React defaults + CSP; `unsafe-inline`/`unsafe-eval` remain Next practical residual | Honest residual |

**Security verdict for RC:** Acceptable for audit / pilot staging with known residuals. **Not** a claim of hardened commercial auth (SSO/MFA/HttpOnly sessions).

---

## 5. Accessibility

| Suite | Result |
|---|---|
| `npm run test:a11y` | **18/18 PASS** |
| Included in `test:quality` | **PASS** |
| Field axe / SR smoke / full WCAG 2.2 AA marketing claim | **OPEN** (prior a11y certification) |

No a11y redesign. No clear keyboard regressions introduced by EPS-003 (docs + version + header hygiene).

---

## 6. Documentation

| Artefact | Status |
|---|---|
| [`RELEASE_NOTES_v2.0_RC.md`](./RELEASE_NOTES_v2.0_RC.md) | Added |
| [`RC4_KNOWN_LIMITATIONS.md`](./RC4_KNOWN_LIMITATIONS.md) | Added |
| [`RC4_PRODUCTION_CHECKLIST.md`](./RC4_PRODUCTION_CHECKLIST.md) | Added |
| [`RC4_ARCHITECTURE_FREEZE.md`](./RC4_ARCHITECTURE_FREEZE.md) | Added |
| [`RC4_TECHNICAL_DEBT.md`](./RC4_TECHNICAL_DEBT.md) | Added |
| [`RC4_FUTURE_ROADMAP.md`](./RC4_FUTURE_ROADMAP.md) | Added |
| Root `VERSION` / manifests / README | Synced to **2.0.0-rc.1** / channel `rc` |
| Historical RC3 / GA cert reports | **Not rewritten** — remain authoritative for their decisions |
| Ops runbooks (GA-004) | Still valid for pilot; RC points to them |

---

## 7. Testing

| Suite | Result | Notes |
|---|---|---|
| `packages/enterprise/tests/test_enterprise.py` | **6 PASS** | Org/RBAC/billing honesty |
| `packages/api_platform/tests/test_enterprise_api.py` | **6 PASS** | Schema, portal, secret non-leak, audit DELETE 403 |
| `apps/web` `test:a11y` | **18 PASS** | |
| `apps/web` `test:quality` | **30 PASS** | a11y + performance automation |
| `release-smoke` + `commercial-readiness` | **7 PASS** | Version channel assertions updated to RC |
| `commercial.test.tsx` onboarding | **Fixed** | No longer requires silent `AAPL` in tutorial copy (GA-C6) |
| Full monorepo pytest / full Vitest / `next build` | **Not claimed complete in this window** | Honest gap — recommend CI gate before tag |
| Coverage % | **Not invented** | Targeted suites green; no fake 100% claim |

---

## 8. Technical Debt

See [`RC4_TECHNICAL_DEBT.md`](./RC4_TECHNICAL_DEBT.md). Top RC-relevant items:

1. In-memory enterprise store  
2. Null billing adapter only  
3. HttpOnly cookie sessions / SSO / MFA incomplete  
4. Universal trust-ladder chrome incomplete  
5. Headed Visual QA + Firefox/Safari smoke unpublished  
6. Next transitive npm advisories (postcss/sharp) without safe non-breaking bump  

---

## 9. Remaining Risks

| ID | Risk | Severity for RC | Severity for Commercial GA |
|---|---|---|---|
| R1 | Enterprise data lost on process restart (in-memory) | **HIGH** for multi-replica prod | **CRITICAL** |
| R2 | No real billing / checkout | Accepted for RC | **CRITICAL** |
| R3 | Enterprise identity via `X-User-Id` foundation | **HIGH** if exposed publicly | **CRITICAL** |
| R4 | Trust ladder not universal | HIGH residual | **CRITICAL** (per GA-005) |
| R5 | Visual QA / browser / field CWV evidence gaps | Process residual | **CRITICAL** |
| R6 | CSP `unsafe-inline` / `unsafe-eval` | Medium residual | Medium–High |
| R7 | Working tree may contain unrelated WIP outside this commit | Ops hygiene | Process |

---

## 10. Release Recommendation

| Question | Answer |
|---|---|
| Suitable as **Version 2.0 Release Candidate** for independent audit? | **YES** |
| Suitable for closed-beta / institutional pilot under Research Mode? | **YES** (with limitations packet) |
| Suitable for unrestricted **Commercial GA**? | **NO** |
| Feature freeze held? | **YES** |
| Recommendation | **PROCEED AS RC** — do not market as Commercial GA |

---

## 11. Commercial Readiness (honest)

| Dimension | Status |
|---|---|
| Enterprise org/teams/RBAC foundation | Shipped (EPS-002) |
| Licensing model + Null billing honesty | Shipped |
| Production billing provider | **Missing** |
| Durable enterprise persistence | **Missing** |
| Self-serve registration / purchasable editions | **Not authorized** |
| Prior Commercial GA decision | **REJECTED** (GA-005) — still stands |
| RC commercial claim | **Conditional / foundation only** |

**Commercial readiness: NOT APPROVED for Commercial GA.** RC hardening prepares audit and deployment planning only.

---

## 12. Alignment

| Reference | Role |
|---|---|
| [`RC3_FINAL_CERTIFICATION_REPORT.md`](./RC3_FINAL_CERTIFICATION_REPORT.md) | Pilot UI freeze authority (1.0.0 era) |
| [`GA_CERTIFICATION_REPORT.md`](./GA_CERTIFICATION_REPORT.md) | Commercial GA REJECTED |
| [`docs/reviews/EPS_002_ENTERPRISE_PLATFORM_REPORT.md`](../reviews/EPS_002_ENTERPRISE_PLATFORM_REPORT.md) | Enterprise foundation scope |
| Tier-0 CV / RS / thin client | Non-negotiable — preserved |

---

## 13. Implementation return (EPS-003)

| Field | Value |
|---|---|
| Architecture Impact | Feature/engine freeze; version channel → RC; docs package; minor header/CSP/env hygiene |
| Components Added | Release artefacts under `docs/releases/` only (no product components) |
| Pages Updated | In-app release-notes doc copy synced to RC |
| Feature Flags Used | None added; enterprise/research flags documented in `.env.example` |
| Accessibility Validation | a11y suite 18/18 PASS |
| Performance Validation | quality suite 30/30 PASS; field LHCI still open |
| Responsive Validation | Covered by existing a11y-responsive automation |
| Known Limitations | [`RC4_KNOWN_LIMITATIONS.md`](./RC4_KNOWN_LIMITATIONS.md) |
| Future Enhancements | [`RC4_FUTURE_ROADMAP.md`](./RC4_FUTURE_ROADMAP.md) |
| Regression Summary | Enterprise + targeted web quality/release suites green; research engines untouched |
