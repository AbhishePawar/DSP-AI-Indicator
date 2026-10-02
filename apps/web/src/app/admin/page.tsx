"use client";

/**
 * EPIC-F008 — Enterprise Administration Console landing page.
 */

import { Suspense } from "react";

import { AuthGuard } from "@/components/auth/ProtectedRoute";
import { AdminConsole } from "@/components/admin-console";
import { WorkspaceSkeleton } from "@/components/admin-console/Primitives";
import { PageHeader } from "@/components/layout/PageHeader";

export default function AdminPage() {
  return (
    <AuthGuard>
      <div className="space-y-4">
        <PageHeader
          title="Admin Panel"
          description="System administration · User management. Counts and accounts come from /api/v1/admin."
        />
        <Suspense fallback={<WorkspaceSkeleton />}>
          <AdminConsole />
        </Suspense>
      </div>
    </AuthGuard>
  );
}
