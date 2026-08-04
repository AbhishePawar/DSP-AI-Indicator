# EPIC-A009 — API Guide

Institutional RBAC routes (additive). Legacy `POST /auth/login` unchanged.

Base: `/api/v1`

| Method | Path | Purpose |
|---|---|---|
| GET | `/auth/rbac/schema` | Schema descriptor |
| POST | `/auth/rbac/login` | Login → tokens + session |
| POST | `/auth/rbac/logout` | Revoke session |
| POST | `/auth/rbac/refresh` | Refresh access token |
| GET | `/auth/rbac/me` | Current user (`Authorization: Bearer`) |
| POST | `/auth/rbac/users` | Create user |
| GET | `/auth/rbac/users` | List users |
| GET | `/auth/rbac/users/{id}` | Get user |
| PUT | `/auth/rbac/users/{id}/roles` | Assign roles |
| GET | `/auth/rbac/roles` | List roles |
| POST | `/auth/rbac/roles` | Upsert role |
| GET | `/auth/rbac/permissions` | List permissions |
| POST | `/auth/rbac/evaluate` | Evaluate permission |
| POST | `/auth/rbac/protect?permission=` | Optional bearer+permission guard |

Default platform APIs remain open for backward compatibility. Callers opt into
protection via `/auth/rbac/protect` or `DSPPlatform.protect_with_permission`.
