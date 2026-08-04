# EPIC-A009 — Auth Architecture

## Layers

```
Client
  │
  ▼
Authentication Service  (login / logout / refresh / password verify / sessions)
  │
  ▼
Authorization Service   (roles / permissions / policies / evaluation)
  │
  ▼
Protected Platform Services (optional guards)
```

## Components

| Module | Responsibility |
|---|---|
| `users.py` | User CRUD via A008 metadata |
| `hashing.py` | PBKDF2 password hashes (stdlib) |
| `jwt.py` | HS256 JWT issue/decode (stdlib) |
| `sessions.py` | Active sessions + revocation |
| `authentication.py` | Login / logout / refresh |
| `authorization.py` | Permission evaluation |
| `roles.py` / `permissions.py` | Configurable RBAC catalogue |
| `service.py` | Public `AuthService` façade |
| `dsp_platform.auth_facade` | Thin platform wiring |

## Determinism

- Fixed `password_salt` → identical hash
- Fixed `issued_at` + `token_id` → identical JWT
- Role/permission maps are frozen tuples

## Persistence

Users: `metadata` id `auth-user-{user_id}`  
Sessions: `metadata` id `auth-session-{session_id}`  

Never stores research payloads (`research_object`, `institutional_report`, `analysis_payload`).

## Non-goals

No changes to research engines, valuation, workflow state machines, or A008 package APIs.
