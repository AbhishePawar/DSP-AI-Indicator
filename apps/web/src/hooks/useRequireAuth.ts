"use client";

import { useAuth } from "@/lib/auth/AuthProvider";
import { loginRedirectUrl, requiresAuth } from "@/lib/auth/routeGuards";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

/** Redirect to login when a protected route is accessed without a session. */
export function useRequireAuth(): ReturnType<typeof useAuth> {
  const auth = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (auth.status === "loading" || auth.status === "refreshing") return;
    if (!auth.session && requiresAuth(pathname)) {
      const target =
        auth.status === "expired"
          ? `${loginRedirectUrl(pathname)}&expired=1`
          : loginRedirectUrl(pathname);
      router.replace(target);
    }
  }, [auth.status, auth.session, pathname, router]);

  return auth;
}
