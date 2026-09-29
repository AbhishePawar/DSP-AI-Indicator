"use client";

/**
 * /admin/control-center — Super Admin configuration registry, branding,
 * flags, rules and platform OS (moved from /control-center, which is now the
 * Figma user-settings page). Access is enforced server-side on
 * /api/v1/control-center/* and mirrored by the shell registry.
 */

import { Suspense, lazy } from "react";

import { Skeleton } from "@/components/ds";
import { PageHeader } from "@/components/layout/PageHeader";

const ControlCenter = lazy(() =>
  import("@/components/control-center").then((m) => ({
    default: m.ControlCenter,
  })),
);

export default function AdminControlCenterPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-4 p-6">
          <PageHeader title="Super Admin Control Center" description="Loading…" />
          <Skeleton className="h-40 w-full" />
        </div>
      }
    >
      <ControlCenter />
    </Suspense>
  );
}
