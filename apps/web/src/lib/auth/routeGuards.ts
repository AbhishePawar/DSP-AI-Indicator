/** Route protection rules — EPIC-008 auth model + F002 auth screens. */

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
  "/admin",
] as const;

export const AUTH_PUBLIC_PATHS = [
  "/login",
  "/signup",
  "/forgot-password",
  "/reset-password",
  "/verify-email",
  "/verification-pending",
  "/session-expired",
  "/unauthorized",
  "/forbidden",
  "/logout",
] as const;

/** P9.1 public marketing website — no app shell sidebar. */
export const MARKETING_PUBLIC_PATHS = [
  "/",
  "/about",
  "/contact",
  "/pricing",
  "/faq",
] as const;

export function normalizePath(pathname: string): string {
  if (!pathname || pathname === "/") return "/dashboard";
  return pathname.endsWith("/") && pathname.length > 1
    ? pathname.slice(0, -1)
    : pathname;
}

/** Strip trailing slash without remapping `/` to dashboard (marketing home). */
export function canonicalizePath(pathname: string): string {
  if (!pathname) return "/";
  if (pathname === "/") return "/";
  return pathname.endsWith("/") && pathname.length > 1
    ? pathname.slice(0, -1)
    : pathname;
}

export function isMarketingPath(pathname: string): boolean {
  const path = canonicalizePath(pathname);
  return MARKETING_PUBLIC_PATHS.some(
    (route) => path === route || (route !== "/" && path.startsWith(`${route}/`)),
  );
}

export function isAuthPublicPath(pathname: string): boolean {
  if (isMarketingPath(pathname)) return true;
  const path = normalizePath(pathname);
  return AUTH_PUBLIC_PATHS.some(
    (route) => path === route || path.startsWith(`${route}/`),
  );
}

export function isPublicRoute(pathname: string): boolean {
  if (isMarketingPath(pathname)) return true;
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

export function loginRedirectUrl(nextPath: string, expired = false): string {
  const next = encodeURIComponent(normalizePath(nextPath));
  return expired
    ? `/login?expired=1&next=${next}`
    : `/login?next=${next}`;
}
