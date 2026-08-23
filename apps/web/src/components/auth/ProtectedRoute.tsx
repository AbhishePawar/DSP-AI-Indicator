"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { Alert } from "@/components/ds";
import { Skeleton } from "@/components/ds";
import { useAuth } from "@/lib/auth/AuthProvider";
import { loginRedirectUrl, requiresAuth } from "@/lib/auth/routeGuards";

export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { status, session } = useAuth();

  useEffect(() => {
    if (status === "restoring" || status === "loading" || status === "refreshing") return;
    if (status === "expired" && requiresAuth(pathname)) {
      router.replace(loginRedirectUrl(pathname, true));
      return;
    }
    if (!session && requiresAuth(pathname)) {
      router.replace(loginRedirectUrl(pathname));
    }
  }, [status, session, pathname, router]);

  if (status === "restoring" || status === "loading" || status === "refreshing") {
    return (
      <div className="space-y-3 p-6" aria-busy="true" aria-label="Loading authentication">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (status === "expired") {
    return (
      <div className="p-6">
        <Alert variant="warning" title="Session expired">
          Your session has expired. Please sign in again.
        </Alert>
      </div>
    );
  }

  if (!session && requiresAuth(pathname)) {
    return (
      <div className="space-y-3 p-6" aria-busy="true" aria-label="Redirecting to sign in">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-20 w-full" />
      </div>
    );
  }

  return <>{children}</>;
}

/** @deprecated Prefer AuthGuard — alias for compatibility. */
export const ProtectedRoute = AuthGuard;
