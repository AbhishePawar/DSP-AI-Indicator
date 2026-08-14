# Architecture Freeze Report — Version 2.0 RC (EPS-003)

| Field | Value |
|---|---|
| Version | **2.0.0-rc.1** |
| Freeze type | Feature / engine / UX redesign freeze |
| Date | 2026-08-02 |
| Tip baseline | `5a64ee8` (EPS-002) |

---

## 1. Freeze scope (must not change behaviour)

| Domain | Status |
|---|---|
| Research engines (Valuation, BQ, Management, Moat, Risk, …) | **FROZEN** |
| AI Committee / Explainability / RI / Comparison / Portfolio logic | **FROZEN** |
| REP-002 presentation contracts | **FROZEN** |
| Trust / GOV-001 honesty rules | **FROZEN** |
| Thin client boundary | **FROZEN** |
| Analyse `/api/v1` contract label `v1.0.0` | **FROZEN** (label + behaviour) |

Hardening allowed: docs, version metadata, headers, env hygiene, tests asserting honesty, ops wiring docs.

---

## 2. Removals performed in EPS-003

| Item | Action |
|---|---|
| Product modules / dead routes | **None removed** (conservative) |
| Unused npm packages | **None removed** without usage proof |
| Temporary feature flags | **None deleted** — enterprise/research flags retained and documented |
| Historical cert docs | **Not deleted / not rewritten** |

EPS-003 preferred documentation of candidates over risky deletes amid a dirty unrelated working tree.

---

## 3. Candidate removals / cleanups (documented — not executed)

| Candidate | Why candidate | Why not removed now |
|---|---|---|
| AUX / Advisor route trees | Outside primary IA; palette non-searchable | Still referenced; demotion-by-IA is intentional product scope, not proven dead |
| Duplicate advisor sidebar patterns | Possible shared-utility consolidation | Behaviour risk; out of RC “no redesign” |
| Untracked WIP (`apps/web/src/foundation/**` extras, `packages/workspace`, large untracked docs) | Not part of EPS-002 tip | Unclear ownership; must not be swept into RC commit blindly |
| Legacy GA-candidate copy in older docs | Stale channel language | Historical; RC docs + README/version sync address living channel |
| `SAMPLE_ANALYSIS_SYMBOL = "AAPL"` in commercial package | Looks like demo ticker | Packaging constant — not silent form default; leave pending product decision |
| Force-upgrade Next to clear postcss/sharp advisories | Advisory noise | Breaking (`audit fix --force` → ancient Next) |

---

## 4. Safe cleanups applied

| Change | Rationale |
|---|---|
| Version channel → `2.0.0-rc.1` / `rc` | Honest RC identity |
| CSP `object-src 'none'` | Genuine header hardening |
| API `X-Permitted-Cross-Domain-Policies: none` | Genuine header hardening |
| `.env.example` / `.env.production.example` hygiene | Secret & RC channel clarity |
| Onboarding test AAPL assertion fix | Align tests to honest copy |
| RC documentation pack | Audit artefacts |

---

## 5. Freeze statement

The platform enters **Version 2.0 RC architecture freeze**: no new analytical capabilities, no engine redesign, no UX redesign under the RC programme. Future work that changes frozen domains requires explicit governance exception and is out of EPS-003.

---

## 6. Related

- [`RC4_TECHNICAL_DEBT.md`](./RC4_TECHNICAL_DEBT.md)  
- [`RC4_RELEASE_CANDIDATE_REPORT.md`](./RC4_RELEASE_CANDIDATE_REPORT.md)  
- [`docs/reviews/EPS_002_ENTERPRISE_PLATFORM_REPORT.md`](../reviews/EPS_002_ENTERPRISE_PLATFORM_REPORT.md)
