"use client";

export const dynamic = "force-dynamic";

import { Suspense } from "react";
import { AuthGuard } from "@/components/auth/ProtectedRoute";
import { PageHeader } from "@/components/layout/PageHeader";
import { AnalyticsWorkspace } from "@/components/admin-panel/AnalyticsWorkspace";
import { WorkspaceSkeleton } from "@/components/admin-console/Primitives";
import Link from "next/link";

export default function AdminAnalyticsPage() {
  return (
    <AuthGuard>
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Link
            href="/admin"
            className="text-xs text-[var(--muted)] hover:text-[var(--text)] transition-colors"
          >
            ← Admin
          </Link>
          <span className="text-xs text-[var(--muted)]">/</span>
          <span className="text-xs text-[var(--text)]">Analytics</span>
        </div>

        <PageHeader
          title="Research Analytics"
          description="Research patterns, metric drill-downs, portfolio activity, and user growth trends."
        />

        <Suspense fallback={<WorkspaceSkeleton />}>
          <AnalyticsWorkspace />
        </Suspense>
      </div>
    </AuthGuard>
  );
}
