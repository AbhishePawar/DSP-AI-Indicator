# Authentication Flow (PEP-001)

## Password login (preferred when hash present)

```mermaid
sequenceDiagram
    participant C as Client
    participant API as api_platform
    participant S as security_platform
    participant DB as DatabasePort
    participant R as SessionPort / RefreshStore

    C->>API: POST /auth/login {username, password?}
    API->>S: IdentityService.authenticate
    S->>DB: load user
    alt has password_hash
        S->>S: verify password + lockout checks
    else RC passwordless compat
        S->>S: allow username-only if no hash
    end
    S->>R: create session + refresh token
    S->>S: issue access JWT (jti)
    S-->>C: access_token (+ refresh_token additive)
```

## Refresh rotation

```mermaid
sequenceDiagram
    participant C as Client
    participant S as security_platform
    C->>S: refresh_token
    S->>S: validate + revoke old refresh
    S->>S: issue new access + refresh
    S-->>C: token pair
```

## API key

Unchanged: `api_key_id` + `api_key_secret` or `Authorization: ApiKey …`.

## OIDC / enterprise multi-provider

Implemented via `EnterpriseAuthPlatform` (see [AUTH_ENTERPRISE_PLATFORM.md](AUTH_ENTERPRISE_PLATFORM.md)):

Client redirects to IdP → authorization code + **PKCE** → API callback → link/create user → **same** local session + JWT/cookies. Not Auth.js.

Passwordless username login is deprecated once OIDC or password+MFA is mandatory in production profile.

## Logout

Revoke refresh token(s), delete session, optional denylist access `jti`.
