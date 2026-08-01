"use client";

import type { ReactNode } from "react";

import { PermissionWrapper } from "@/components/ds";
import { useAuth } from "@/lib/auth/AuthProvider";

export function AuthPermissionGate({
  permission,
  children,
  fallback,
}: {
  permission: string;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { session, user } = useAuth();
  const allowed = Boolean(session) && (
    user?.permissions.includes(permission) === true ||
    user?.roles.includes("administrator") === true
  );

  return (
    <PermissionWrapper allowed={allowed} fallback={fallback}>
      {children}
    </PermissionWrapper>
  );
}
