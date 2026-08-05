# EPIC-A009 — API Guide

Institutional RBAC routes (additive). Legacy `POST /auth/login` unchanged.

Base: `/api/v1`

| Method | Path | Purpose |
|---|---|---|
| GET | `/auth/rbac/schema` | Schema descriptor |
| POST | `/auth/rbac/login` | Login → tokens + session |
| POST | `/auth/rbac/logout` | Revoke session |
| POST | `/auth/rbac/refresh` | Rotate refresh token → new access + refresh tokens |
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

## Refresh token rotation

`POST /auth/rbac/refresh` implements OAuth 2.0 Security BCP rotation, not a
stateless re-issue: the response's `tokens.refresh_token` is a **new**
value on every call, and the token you sent becomes permanently invalid
the instant the response is returned — do not cache or retry with it.

Request:

```json
{ "refresh_token": "<current refresh token>" }
```
(`refresh_token` may be omitted when using cookie auth — the `dsp_refresh`
HttpOnly cookie is read instead. `created_at` / `access_jti` remain
optional, deterministic-testing-only fields, unchanged from before.)

Response (`200`) — identical shape to `/auth/rbac/login`:

```json
{
  "ok": true,
  "result": {
    "user": { "...": "..." },
    "tokens": {
      "access_token": "...",
      "refresh_token": "... (new — the old one is now dead)",
      "token_type": "bearer",
      "expires_in": 3600,
      "session_id": "..."
    },
    "session": { "session_id": "...", "revoked": false, "...": "..." }
  },
  "message": null
}
```

Failure (`401`) — invalid, expired, revoked, or **already-used** refresh
token. A `401` here always means "the client must re-authenticate", never
"retry the request": if the token was rejected because it had already been
rotated away (reuse/replay), the **entire session has been revoked** as a
side effect, so retrying — even with a token from a response that
appeared to succeed moments earlier in a race — will also fail. Clients
should treat this exactly like an expired session: drop local tokens and
send the user back through the login flow.

```json
{ "ok": false, "error": "Refresh token reuse detected; session revoked.", "message": "Data unavailable." }
```

See [SECURITY_GUIDE.md](SECURITY_GUIDE.md#refresh-token-rotation--reuse-detection-oauth-20-security-bcp) and [ENTERPRISE_AUTH_PLATFORM.md §3e](security/ENTERPRISE_AUTH_PLATFORM.md) for the full design, audit event catalogue, and sequence diagrams.
