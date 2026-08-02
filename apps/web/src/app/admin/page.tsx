"use client";

/**
 * EPIC-F008 — Enterprise Administration Console landing page.
 */

import { Suspense } from "react";

import { AdminConsole } from "@/components/admin-console";
import { WorkspaceSkeleton } from "@/components/admin-console/Primitives";
import { PageHeader } from "@/components/layout/PageHeader";

export default function AdminPage() {
  return (
    <div className="space-y-4">
      <PageHeader
        title="Enterprise Administration"
        description="Operational visibility from certified A010 /api/v1/admin APIs. Display-only — no client-side administration logic."
      />
      <Suspense fallback={<WorkspaceSkeleton />}>
        <AdminConsole />
      </Suspense>
    </div>
  );
}
