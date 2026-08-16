# DSP AI Indicator — PRD / Working Notes

## Product
Institutional-grade, explainable equity-research platform (Python monorepo, FastAPI api_platform on :8000 + Next.js apps/web, Postgres). Authoritative lineage: 7636fb2.

## Implemented (dated)
- 2026-08 Exchange-handoff fix (commit 676c84a): public `exchange` threaded API->CompositionRequest->Upstox resolver; Upstox statement adapter fail-closed with real status. 23/23 focused tests. Branch: fix/asi003-dsp-platform-boundaries.
- 2026-08 Email & password auth (BACKEND): extended existing security_platform IdentityService.
  - `POST /api/v1/auth/register` (email+password -> JWT, role CLIENT; email is username)
  - `GET  /api/v1/auth/me` (cookie or Bearer -> profile)
  - Idempotent admin seed via DSP_ADMIN_EMAIL/DSP_ADMIN_PASSWORD (default admin@dsp.ai / DspAdminPass2026, role ADMIN)
  - Added /auth/register + /auth/session to security middleware public paths
  - Reuses existing /auth/login, /auth/refresh, /auth/logout, Argon2/scrypt hashing, lockout, CSRF
  - Tests: packages/api_platform/tests/test_email_password_auth.py (6/6 pass)
  - Enable with DSP_ENABLE_SECURITY=true, DSP_JWT_SECRET set.

## NOT done / deferred
- P0: Next.js (apps/web) login/register UI + session wiring — backend ready, frontend NOT built (cannot run/test Next.js in this sandbox).
- P1: Persist users in Postgres for the running API (SecurityBundle.create uses in-memory UserStore by default; SqlUserRepository path exists via create_with_infrastructure but not wired into build_default_platform).
- P1: Password reset / email verification endpoints (service methods exist; HTTP not exposed).
- Pre-existing (base 7636fb2): 12+ failing tests (version-string drift 0.3.0 vs 1.0.0, architecture/boundary, compare workflow) — unrelated to this work.

## Test credentials
See /app/memory/test_credentials.md
