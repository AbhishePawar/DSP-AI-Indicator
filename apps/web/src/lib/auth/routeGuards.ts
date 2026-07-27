/** Route protection rules — EPIC-008 auth model. */

export const PUBLIC_ROUTE_PREFIXES = [
  "/dashboard",
  "/companies",
  "/research",
  "/analysis",
] as const;

export const PROTECTED_ROUTE_PREFIXES = [
  "/portfolio",
  "/copilot",
  "/diagnostics",
  "/profile",
] as const;

export const AUTH_PUBLIC_PATHS = ["/login"] as const;

export function normalizePath(pathname: string): string {
  if (!pathname || pathname === "/") return "/dashboard";
  return pathname.endsWith("/") && pathname.length > 1
    ? pathname.slice(0, -1)
    : pathname;
}

export function isAuthPublicPath(pathname: string): boolean {
  const path = normalizePath(pathname);
  return AUTH_PUBLIC_PATHS.some(
    (route) => path === route || path.startsWith(`${route}/`),
  );
}

export function isPublicRoute(pathname: string): boolean {
  const path = normalizePath(pathname);
  if (isAuthPublicPath(path)) return true;
  return PUBLIC_ROUTE_PREFIXES.some(
    (route) => path === route || path.startsWith(`${route}/`),
  );
}

export function isProtectedRoute(pathname: string): boolean {
  const path = normalizePath(pathname);
  return PROTECTED_ROUTE_PREFIXES.some(
    (route) => path === route || path.startsWith(`${route}/`),
  );
}

export function requiresAuth(pathname: string): boolean {
  return isProtectedRoute(pathname);
}

export function loginRedirectUrl(nextPath: string): string {
  const next = encodeURIComponent(normalizePath(nextPath));
  return `/login?next=${next}`;
}
