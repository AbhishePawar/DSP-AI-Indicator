import type { ReactNode } from "react";

export type PermissionWrapperProps = {
  allowed: boolean;
  children: ReactNode;
  fallback?: ReactNode;
};

/**
 * Pure UI gate — callers supply `allowed`; no auth/API logic here.
 */
export function PermissionWrapper({
  allowed,
  children,
  fallback = null,
}: PermissionWrapperProps) {
  if (!allowed) return <>{fallback}</>;
  return <>{children}</>;
}
