# EPIC-014 — Production Readiness Audit & v1.0.0 Preparation

| Field | Value |
|---|---|
| **Version** | `1.0.0` |
| **Status** | **Complete** (audit) |
| **Last updated** | 2026-07-27 |
| **Scope** | Engineering validation only — no investment-logic changes |
| **API RC under review** | `v1.0.0-rc1` |

---

## 1. Executive Summary

EPIC-014 audited the full monorepo for promotion from **`v1.0.0-rc1` → `v1.0.0`**.

**Backend / platform core is production-viable:** repository integrity PASS, import cycles NONE, **2601 / 2601** Python tests PASS, security health-path gap fixed, `llm_adapters` integrity restored, root Docker compose restored, and application import allowlists expanded to cover FEATURE domains.

**Full product GA is not yet recommended** because restoring `apps/web/src/lib` (previously hidden by a root `.gitignore` rule `lib/`) revealed a large thin-client violation: client-side moat / valuation / management / earnings **scoring engines** live in TypeScript. That contradicts frozen architecture (no investment math in the browser). Remediating those engines is out of scope for this epic and requires an explicit thin-client remediation epic or freeze amendment.

| Layer | Verdict |
|---|---|
| Python packages / engines | **Validated** |
| `/api/v1` + security health probes | **Validated** (after EPIC-014 fixes) |
| Architecture tests / cycles | **Validated** |
| Vitest (web unit) | **104 PASS** |
| Thin-client invariant (web) | **FAIL — blocker for GA** |
| Docker CLI on audit host | Not installed (compose file restored; runtime not executed) |

---

## 2. Repository Health Score

| Dimension | Score | Notes |
|---|---|---|
| Package integrity | **98** | 38 registered packages; integrity PASS; `llm_adapters` `__version__` fixed |
| Architecture / cycles | **95** | Cycles NONE; façade scan GREEN after allowlist + BOM-safe read |
| Backend / API | **94** | Health/live/ready public under security; composition tests PASS |
| Security | **88** | Health paths fixed; rate-limit hook still non-enforcing; passwordless RC login |
| Frontend presentation tests | **92** | 104 Vitest PASS |
| Thin-client compliance | **55** | Extensive TS scoring under `apps/web/src/lib/{moat,valuation,management,earnings}` |
| Documentation consistency | **90** | Public API versions aligned; STATUS lag remains |
| Ops / Docker | **85** | Root compose restored; Docker binary absent on audit machine |
| **Overall** | **86 / 100** | Up from prior 91 on engines; GA blocked by thin-client debt |

---

## 3. Architecture Review

### Clean Architecture / DDD
- Package boundaries and ownership matrix remain coherent.
- `dsp_platform` composition root intact.
- Application import rule: apps may import only `dsp_platform` + `contracts` (HTTP clients for web).

### Dependency direction
- First-party cycle scan: **NONE**.
- Façade parity test GREEN after:
  - Expanding `FORBIDDEN_APPLICATION_PACKAGES` / `PLATFORM_PACKAGES`
  - Allowing `copilot.enums` / `copilot.models` for LLM adapters
  - Removing deep `llm_adapters.registry` import from API dependencies
  - Reading sources with `utf-8-sig` (financial `__init__.py` carries a UTF-8 BOM — **not modified** per DO NOT MODIFY)

### Thin client
| Check | Result |
|---|---|
| Web imports Python engines | CLEAN |
| MapResponse / API clients | Presentation-only |
| Client-side DCF / moat / earnings scoring modules | **VIOLATION** (large `lib/moat`, `lib/valuation`, etc.) |

### Single ownership
- Dual packages (`ai_committee` vs `investment_committee`, `recommendation` vs `investment_recommendation`) remain intentional and documented.
- Orphan `packages/data-ingestion/` remains unregistered (ADR-ASI-002-002).

### Version consistency (key packages)
| Package | Matrix | `__version__` | pyproject |
|---|---|---|---|
| `dsp_platform` | 0.7.1 | 0.7.1 | 0.7.1 |
| `api_platform` | 0.2.0 | 0.2.0 | 0.2.0 |
| `valuation` | 0.12.0 | aligned | aligned |
| `financial` | 0.7.0 | aligned | aligned |
| `llm_adapters` | 0.1.0 | **0.1.0 (fixed)** | 0.1.0 |

Doc/product skew: `dsp-web` package.json = `3.0.0-rc1` vs STATUS checkpoint `2.5.0`.

---

## 4. Bugs Found

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| B-001 | **Critical** | `.gitignore` `lib/` ignored entire `apps/web/src/lib` (408 TS files untracked) | **Fixed** — ignore narrowed to `/lib/`; files staged |
| B-002 | **High** | Prod security public paths omitted `/health/live`, `/health/ready`, `/metrics` | **Fixed** |
| B-003 | **High** | `llm_adapters` missing `__version__` → integrity FAIL | **Fixed** |
| B-004 | **High** | App import allowlist omitted FEATURE / Phase 2–3 packages | **Fixed** |
| B-005 | **High** | Empty root `docker-compose.yml` | **Fixed** — `include` → `docker/docker-compose.yml` |
| B-006 | **Medium** | `/analyse` / copilot complete/stream missing from `PATH_PERMISSIONS` | **Fixed** |
| B-007 | **Medium** | Stale test expectations (`dsp_platform` 0.6.0, api deps without `llm_adapters`) | **Fixed** |
| B-008 | **Medium** | Deep import `llm_adapters.registry` from API | **Fixed** — public façade |
| B-009 | **High (GA)** | Client-side investment scoring engines in web `lib/` | **Documented** — requires dedicated remediation epic |
| B-010 | **Medium** | `RateLimitHookMiddleware` does not enforce limits | Accepted debt (edge expected) |
| B-011 | **Medium** | Passwordless username login; advisor routes largely unprotected | Accepted RC limitation |
| B-012 | **Low** | UTF-8 BOM in `packages/financial/.../intelligence/__init__.py` | Observed; **not modified** (DO NOT MODIFY financial) |
| B-013 | **Low** | OpenAPI / docs version drift | Partially fixed in PUBLIC_API_REFERENCE / VERSION_MATRIX |

---

## 5. Files Modified (EPIC-014)

Investment engines (**not** modified): valuation, financial calc, recommendation, investment_committee, scoring methodologies, public API route contracts.

| Path | Change |
|---|---|
| `.gitignore` | Root-only `/lib/` `/lib64/` |
| `docker-compose.yml` | Restored via compose `include` |
| `packages/security_platform/.../auth.py` | Public health/metrics/version paths |
| `packages/security_platform/.../middleware.py` | PATH_PERMISSIONS for analyse/validate/copilot |
| `packages/security_platform/tests/test_security.py` | Probe health/live/ready/metrics |
| `packages/llm_adapters/src/llm_adapters/__init__.py` | `__version__` |
| `packages/llm_adapters/tests/test_architecture.py` | New |
| `packages/llm_adapters/README.md` | New |
| `packages/dsp_platform/.../boundaries.py` | Expanded allowlists + copilot type prefixes |
| `packages/dsp_platform/tests/test_boundaries.py` | FEATURE assertions + utf-8-sig |
| `packages/dsp_platform/tests/test_platform_integration.py` | Version 0.7.1 |
| `packages/api_platform/.../dependencies.py` | Façade import only |
| `packages/api_platform/tests/test_architecture.py` | Declare `llm_adapters` dep |
| `docs/PUBLIC_API_REFERENCE.md` | Version alignment |
| `docs/PACKAGE_OWNERSHIP_MATRIX.md` | `llm_adapters` row |
| `docs/VERSION_MATRIX.md` | OpenAPI 0.2.0 + `llm_adapters` |
| `apps/web/src/lib/**` | **Staged** (408 files) after gitignore fix — content unchanged |

---

## 6. Performance Findings

| Area | Finding |
|---|---|
| Python suite | 2601 tests in ~20s — healthy |
| Vitest | 104 tests in ~5.6s — healthy |
| API rate-limit hook | Sets budget only; no in-process enforcement |
| Caching | Decision Pack hash caching documented; not re-benchmarked |
| Bundle | `npm run analyze` is a stub; no bundle report generated |
| Docker | Images not built on audit host (Docker absent) |
| Frontend scoring libs | Large TS engine trees increase client bundle risk if imported into routes |

---

## 7. Security Findings

| Area | Status |
|---|---|
| Security headers middleware | Present |
| JWT / auth middleware | Present when `DSP_ENABLE_SECURITY` |
| Health endpoints under security | **Fixed** for live/ready/metrics |
| Composition `/analyse` permission | **Fixed** |
| Secrets | Dev JWT default; `validate_env.py` guards prod profile |
| CORS | Env-driven |
| Rate limiting | Edge-preferred; in-process hook non-blocking |
| Web auth | Client-only; no Next middleware; passwordless RC login |
| CSP | `unsafe-inline` / `unsafe-eval` (Next common; weak for hardened prod) |
| LLM override of deterministic scores | Safety module present; deterministic fallback exists |

---

## 8. Documentation Findings

| Finding | Action |
|---|---|
| PUBLIC_API_REFERENCE package versions stale | Updated |
| VERSION_MATRIX OpenAPI 0.1.0 | Updated to 0.2.0 |
| `llm_adapters` missing from ownership matrix | Added |
| DSP_STATUS / README FEATURE lag | Remaining debt |
| Empty `configs/environments/*.yaml` | Remaining debt |
| Charter suite (PROJECT_CHARTER etc.) | Present (2026-07-27) |

---

## 9. Test Results

| Suite | Result |
|---|---|
| `scripts/ci_repository_integrity.py` | **PASS** (38 packages) |
| `pytest packages` | **2601 PASSED** |
| Architecture / cycles / boundaries | **PASS** |
| `security_platform` + health RC1 | **PASS** |
| `llm_adapters` | **PASS** |
| Vitest `apps/web` | **104 PASSED** (20 files) |
| Docker compose config | Not executed (Docker CLI missing) |
| Live market / live LLM | Not exercised (offline audit) |

---

## 10. Remaining Technical Debt

| ID | Item | Risk | Blocks GA? |
|---|---|---|---|
| TD-E014-01 | Remove or relocate web investment scoring engines to server-only | **High** | **Yes** |
| TD-E014-02 | Align `dsp-web` version with STATUS / release tag | Medium | No |
| TD-E014-03 | Enforce rate limits or document edge-only clearly in ops handbook | Medium | No |
| TD-E014-04 | Harden auth (password / SSO) + Next middleware for advisor routes | High (enterprise) | Soft |
| TD-E014-05 | Strip UTF-8 BOM in financial intelligence `__init__.py` (separate unlock) | Low | No |
| TD-E014-06 | Orphan `data-ingestion/` removal or registration | Medium | No |
| TD-E014-07 | Commit staged `apps/web/src/lib` after review | **High** | Process |
| TD-D006… | Prior debt register items | Medium | No |

Prior register → [asi/TECHNICAL_DEBT_REGISTER.md](asi/TECHNICAL_DEBT_REGISTER.md).

---

## 11. Release Recommendation

### Backend / API RC

Python platform, engines, composition, and `/api/v1` are **validated for continued RC use**. EPIC-014 production fixes (health paths, integrity, allowlists, compose, gitignore) should be committed before any tag cut.

### Product GA (`v1.0.0`)

**Not recommended yet.**

Reason: thin-client violation (client-side valuation / moat / management / earnings scoring) is a Product Constitution / Architecture Governance failure. Promoting to `v1.0.0` without remediation or an explicit freeze amendment would certify a forbidden architecture.

### Required before stating full promotion

1. Commit EPIC-014 fixes + staged `apps/web/src/lib` (visibility).
2. Open **EPIC-015 (Thin Client Remediation)** — delete or quarantine browser scoring engines; bind UI to `/api/v1` envelopes only.
3. Re-run full suites + architecture thin-client scan.
4. Then cut `v1.0.0` if GREEN.

### Explicit statement

> Platform **backend / API RC** validated successfully after EPIC-014 engineering fixes.  
> **Do not** promote the full product from `v1.0.0-rc1` to `v1.0.0` until thin-client remediation (TD-E014-01) is complete or formally waived by architecture freeze amendment.

---

## Related

[DSP_STATUS.md](DSP_STATUS.md) · [VERSION_MATRIX.md](VERSION_MATRIX.md) · [DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md) · [asi/TECHNICAL_DEBT_REGISTER.md](asi/TECHNICAL_DEBT_REGISTER.md)
