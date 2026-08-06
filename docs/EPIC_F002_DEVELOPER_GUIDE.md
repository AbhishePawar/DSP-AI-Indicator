# EPIC-F002 — Developer Guide

```bash
cd apps/web
npm test -- src/lib/auth/auth.test.ts src/components/auth/auth-permission-gate.test.tsx
```

## Key modules

| Module | Role |
|---|---|
| `lib/api/rbacAuth.ts` | A009 client |
| `lib/auth/AuthProvider.tsx` | Login / logout / refresh / me |
| `lib/auth/authStore.ts` | Zustand mirror |
| `lib/auth/sessionStore.ts` | Persistence v3 |
| `components/auth/ProtectedRoute.tsx` | `AuthGuard` |
| `components/auth/AuthPermissionGate.tsx` | Permission UI gate |

## Login

Prefer RBAC: `login({ username, password, rememberMe, useRbac: true })`.
