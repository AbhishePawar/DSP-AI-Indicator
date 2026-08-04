# EPIC-F002 — Authentication Architecture

```
Login / Forgot / Session-expired / 401 / 403 screens
        │
        ▼
AuthProvider  ←→  useAuthStore (Zustand mirror)
        │
        ├─ sessionStore (persist v3)
        ├─ rbacAuthApi → /auth/rbac/{login,logout,refresh,me,evaluate}
        └─ api.login / api.refresh → legacy /auth/*
        │
        ▼
AuthGuard · AuthPermissionGate · Topbar UserMenu
```

## Screens

| Route | Purpose |
|---|---|
| `/login` | Username + password RBAC login |
| `/forgot-password` | UI only (no reset API) |
| `/session-expired` | Expired session CTA |
| `/unauthorized` | 401 |
| `/forbidden` | 403 |
| `/profile` | Account, roles, permissions, sessions, token status |

## Rules

- No backend / API contract / RBAC engine changes
- Missing data → **Data unavailable.**
- Logout-all disabled when backend unavailable
