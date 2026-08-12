/**
 * EPIC-F000 — API strategy (thin client).
 * Backend dsp_platform v1.0.0 · HTTP contract v1.0.0 — unchanged.
 */

export const apiStrategy = {
  transport: "fetch",
  baseUrlEnv: "NEXT_PUBLIC_API_BASE_URL",
  prefix: "/api/v1",
  authHeader: "Authorization: Bearer <access_token>",
  existingClient: "src/lib/api/client.ts",
  rules: [
    "Browser never imports Python packages or engines",
    "No valuation / scoring / recommendation computation in UI",
    "Missing data → display 'Data unavailable.' — never fabricate",
    "Additive institutional routes: /auth/rbac/*, /admin/*, /persistence/*",
    "Legacy /auth/login remains valid",
  ],
  errorModel: {
    type: "ApiClientError",
    surface: { ok: false, error: "string", message: "Data unavailable. | detail" },
  },
  futureModules: {
    rbacClient: "foundation/api/rbac (F001+)",
    adminClient: "foundation/api/admin (F001+)",
  },
} as const;

export type ApiUxState = "idle" | "loading" | "success" | "empty" | "error";

export function resolveListState(
  isLoading: boolean,
  isError: boolean,
  count: number,
): ApiUxState {
  if (isLoading) return "loading";
  if (isError) return "error";
  if (count === 0) return "empty";
  return "success";
}
