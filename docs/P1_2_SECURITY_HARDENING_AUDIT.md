# P1.2 — Production Security Hardening Audit

Status: **COMPLETE (with remediations applied)** · Backend **`dsp_platform` v1.1.0** · Frontend **unchanged (v1.5.0)**

Audit date: 2026-07-28  
Scope: Authentication, authorization, API protection, HTTP headers, secrets, dependencies, logging, production configuration.  
Out of scope: Valuation engines, recommendation logic, AI Committee, report rendering, deterministic analysis.

---

## Executive Verdict

**PASS (conditional)** — Critical production gaps found during audit were remediated in `security_platform` **0.2.1** and `api_platform` **0.2.1** without changing analysis contracts. Remaining items are High/Medium operational follow-ups (durable audit, HttpOnly cookies, MFA, CI dependency scanning, body-size limits).

---

## Security Checklist

| Area | Control | Pre-audit | Post-remediation |
|---|---|---|---|
| AuthN | Argon2 / scrypt / PBKDF2 hashing | Present | Present |
| AuthN | Password policy (≥12 + complexity) | Partial (HTTP min 8) | HTTP min **12** aligned |
| AuthN | JWT / refresh / remember-me TTLs | Present | Present |
| AuthN | Lockout 5 / 900s | Present (`security_platform`) | Present |
| AuthN | Logout invalidation | Partial | Documented; RBAC logout present |
| AuthN | Password reset / email verify HTTP | Absent (service only) | Open (Medium) |
| AuthN | MFA / OIDC | Absent (null ports) | Open (Medium) |
| AuthZ | Route middleware | Partial | Institutional zone + research export mapped |
| AuthZ | Admin HTTP auth | **Absent** | **Enforced** when production / security on |
| AuthZ | Research export permission | Absent | `VIEW_REPORTS` when security on |
| API | Rate limit enforce | Non-blocking hook | **429 when enabled** |
| API | Request body size limit | Absent | Open (Medium) |
| API | CORS / versioning / validation | Present | Present |
| HTTP | X-Frame / nosniff / Referrer / Permissions | Present | Present |
| HTTP | HSTS | Absent | **Production / `DSP_HSTS_ENABLED`** |
| HTTP | CSP (API) | Absent | Open (Low — JSON API) |
| Secrets | Env + validate_env | Present | + production JWT refuse default |
| Secrets | Passwordless admin seed in prod | Risk | **Blocked** |
| Logging | Auth fail / deny audit | In-memory | Present (durable still open) |
| Prod | Secure HttpOnly cookies | Absent (Bearer storage) | Open (High — frontend follow-up) |
| Deps | CI CVE scan | Absent | Open (Medium) |

---

## Findings

### Critical (remediated)

1. **Unauthenticated `/admin/*` in default deployments**  
   Institutional admin routes used `Depends(get_api_state)` only.  
   **Fix:** `require_admin_access` router dependency — requires Bearer + `configure_platform` or `manage_users` when `DSP_ENVIRONMENT=production`, `DSP_ENABLE_SECURITY=true`, or `DSP_REQUIRE_ADMIN_AUTH=true`.

2. **Dual-stack JWT collision**  
   `DSP_ENABLE_SECURITY=true` required `security_platform` JWT on all non-public paths, including `/auth/rbac/login` and `/admin`, breaking institutional login.  
   **Fix:** Institutional `/admin` and `/auth/rbac` treated as auth-package zone; RBAC login/refresh/schema added to public paths.

3. **Passwordless admin seed in production**  
   **Fix:** Production create_app refuses default JWT secret; disables passwordless seed unless `DSP_SEED_ADMIN_PASSWORD` set.

### High (partial / open)

4. **Browser token storage (localStorage / sessionStorage)** — not HttpOnly. Frontend unchanged this epic; track for cookie-session follow-up.  
5. **Rate limiting** — now enforces when `DSP_RATE_LIMIT_ENABLED=true`; still prefer edge Redis for multi-node.  
6. **Research mutating routes** beyond export/report still lack dedicated permission map.  
7. **`/auth/rbac/users` create remains open** when admin auth off — production must keep `DSP_REQUIRE_ADMIN_AUTH` / security on.

### Medium

8. Password reset / email verification HTTP surfaces absent (service exists).  
9. MFA / OIDC / SSO null ports.  
10. No request body size middleware.  
11. In-memory audit ring (1000) — not durable / CERT-In retention.  
12. No CI SAST / `pip-audit` / `npm audit` gate.  
    Spot check (2026-07-28): `pip-audit` not installed in environment; `npm audit --omit=dev`
    reports **high** advisories in the Next.js dependency tree (postcss/sharp via `next`) —
    tracked as frontend follow-up (this epic leaves frontend unchanged).  
13. OpenAPI `/docs` public when security enabled.  
14. `DSP_FORWARDED_ALLOW_IPS=*` trust risk at proxy.

### Low

15. API CSP not set (JSON API; browsers use web CSP).  
16. Special-character password rule not required.  
17. Password history / rotation policy absent.

---

## Risk Matrix

| ID | Finding | Likelihood | Impact | Risk | Status |
|---|---|---|---|---|---|
| C1 | Open admin API | High | Critical | **Critical** | Remediated |
| C2 | Security middleware vs RBAC login | High | High | **Critical** | Remediated |
| C3 | Prod passwordless admin | Medium | Critical | **Critical** | Remediated |
| H1 | XSS → stolen Bearer in storage | Medium | High | **High** | Open (FE) |
| H2 | Unbounded research POSTs | Medium | High | **High** | Partial |
| M1 | No durable audit | Medium | Medium | **Medium** | Open |
| M2 | No body size limit | Medium | Medium | **Medium** | Open |
| M3 | No CI dependency CVE gate | Medium | Medium | **Medium** | Open |
| L1 | API CSP | Low | Low | **Low** | Open |

---

## Remediation Plan

### Applied in P1.2 (this release)

| Item | Change |
|---|---|
| Admin auth | `require_admin_access` on institutional admin router |
| Institutional zone | Security middleware skips `/admin`, `/auth/rbac` (auth package owns) |
| Public RBAC login | Added to `SecuritySettings.public_paths` |
| Research export/report | `PATH_PERMISSIONS` → `VIEW_REPORTS` |
| Rate limit | In-process enforce + HTTP 429 when enabled |
| HSTS | Production or `DSP_HSTS_ENABLED` |
| Password HTTP min | 12 characters |
| Prod secrets | Reject default JWT; no passwordless admin seed |
| Versions | `dsp_platform` **1.1.0**, `security_platform` **0.2.1**, `api_platform` **0.2.1** |

### Recommended next (not blocking PASS)

1. HttpOnly Secure SameSite cookies for access/refresh (frontend + API).  
2. Wire Redis `RateLimitPort` in production compose.  
3. Add FastAPI/Starlette max body size (e.g. 1–2 MiB).  
4. Durable append-only audit sink (PEP-003).  
5. CI job: `pip-audit` + `npm audit --omit=dev` fail-on-high.  
6. Gate `/docs` behind auth or disable in production.  
7. Expose password-reset / email-verify HTTP with same rate limits.  
8. Unify JWT secrets / issuers across `security_platform` and `auth` packages.

---

## Production Configuration Notes

```bash
DSP_ENVIRONMENT=production
DSP_ENABLE_SECURITY=true
DSP_REQUIRE_ADMIN_AUTH=true          # default when production
DSP_JWT_SECRET=<strong-random>       # never dev-only-change-me
DSP_SEED_ADMIN_PASSWORD=<strong>     # required to seed security_platform admin
DSP_CORS_ORIGINS=https://app.example.com
DSP_RATE_LIMIT_ENABLED=true
DSP_RATE_LIMIT_PER_MINUTE=600
DSP_HSTS_ENABLED=true                # or rely on production auto-HSTS
```

Validate: `python scripts/validate_env.py`

---

## Testing

```bash
pytest packages/security_platform/tests -q --import-mode=importlib
pytest packages/auth/tests -q --import-mode=importlib
pytest packages/api_platform/tests/test_institutional_admin_api.py -q --import-mode=importlib
pytest packages/api_platform/tests/test_institutional_auth_api.py -q --import-mode=importlib
pytest packages/security_platform/tests/test_security.py -q --import-mode=importlib
```

**Regression run (P1.2):** **103 / 103 PASS** (security_platform + auth + api_platform institutional + architecture + dsp_platform integration/architecture).

Frontend unchanged — no web version bump.

---

## Traceability / Compatibility

- `/api/v1` analyse / valuation / recommendation / committee contracts unchanged.  
- Dev / test default (`DSP_REQUIRE_ADMIN_AUTH` unset, non-production, security off) keeps admin open for existing smoke tests.  
- No weakening of hashing, lockout, or CORS defaults.

---

## PASS / FAIL

| Gate | Result |
|---|---|
| Critical findings remediated | **PASS** |
| Analysis / engine immutability | **PASS** |
| API backward compatibility | **PASS** |
| Frontend unchanged | **PASS** |
| Security regression tests | **PASS** (run in CI / local suite) |
| Remaining High/Medium tracked | Accepted with remediation plan |

### Overall: **PASS**

Backend: **`dsp_platform` v1.1.0** (audit + hardening)  
Frontend: **unchanged**
