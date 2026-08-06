# EPIC-A009 — Authentication & Role-Based Access Control (RBAC)

Status: **COMPLETE** · Priority: P0 · `dsp_platform` **0.21.0**

## Summary

Deterministic institutional identity, authentication, and authorization for
`dsp_platform`. Introduces user accounts, password hashing, JWT access/refresh
tokens, sessions, roles, and permission evaluation.

**Identity only** — does not change financial models, valuation, research,
workflow logic, persistence package internals, recommendations, or scoring.

## Package

`packages/auth/` → import name `auth`

Persists users/sessions as A008 `metadata` entities (no persistence model changes).

## Docs

| Doc | Path |
|---|---|
| Architecture | [AUTH_ARCHITECTURE.md](AUTH_ARCHITECTURE.md) |
| RBAC Guide | [RBAC_GUIDE.md](RBAC_GUIDE.md) |
| Security Guide | [SECURITY_GUIDE.md](SECURITY_GUIDE.md) |
| API Guide | [API_GUIDE.md](API_GUIDE.md) |
| Developer Guide | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) |

## Compatibility

- Legacy `POST /auth/login` (`security_platform`) unchanged
- New routes under `/api/v1/auth/rbac/*`
- Default API remains open unless callers use `/auth/rbac/protect`

## Final

**PASS** — Authentication & RBAC completed. Research artifacts remain immutable.
Platform behaviour unchanged. `dsp_platform` **v0.21.0**.
