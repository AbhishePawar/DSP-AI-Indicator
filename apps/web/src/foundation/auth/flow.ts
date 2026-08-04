/**
 * EPIC-F000 — Authentication flow freeze (JWT · existing backend APIs).
 */

export const authFlowSpec = {
  legacyLogin: {
    method: "POST",
    path: "/auth/login",
    client: "api.login",
    notes: "security_platform compatible — do not break",
  },
  institutionalRbac: {
    login: "POST /auth/rbac/login",
    refresh: "POST /auth/rbac/refresh",
    logout: "POST /auth/rbac/logout",
    me: "GET /auth/rbac/me",
    protect: "POST /auth/rbac/protect",
    notes: "A009 additive — adopt in F-series behind feature flag if needed",
  },
  session: {
    store: "lib/auth/sessionStore",
    tokenType: "Bearer JWT",
    rules: [
      "Never store password",
      "Attach Bearer on authenticated requests",
      "Clear session on logout / 401 recovery",
    ],
  },
  guards: {
    existing: ["ProtectedRoute", "useRequireAuth", "routeGuards"],
    publicPrefixes: ["/login", "/docs", "/health", "/maintenance"],
  },
} as const;
