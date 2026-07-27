"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { WorkspaceLoading } from "@/components/loading/WorkspaceLoading";
import { Alert } from "@/components/ui/Alert";
import { useAuth } from "@/lib/auth/AuthProvider";
import { loginRedirectUrl, requiresAuth } from "@/lib/auth/routeGuards";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { status, session } = useAuth();

  useEffect(() => {
    if (status === "loading" || status === "refreshing") return;
    if (!session && requiresAuth(pathname)) {
      router.replace(loginRedirectUrl(pathname));
    }
  }, [status, session, pathname, router]);

  if (status === "loading" || status === "refreshing") {
    return <WorkspaceLoading label="Checking session…" />;
  }

  if (!session) {
    return (
      <WorkspaceLoading label="Redirecting to sign in…" />
    );
  }

  if (status === "expired") {
    return (
      <Alert tone="warning" title="Session expired">
        Your session has expired. Please sign in again.
      </Alert>
    );
  }

  return <>{children}</>;
}
