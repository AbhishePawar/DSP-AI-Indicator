"use client";

/**
 * RS-001…RS-010 scroll dashboard — retained alongside the publishing workspace.
 * RC3-004 — dynamic import + skeleton loading for IRD.
 */

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ds";

const InstitutionalDashboardClient = dynamic(
  () =>
    import(
      "@/components/institutional-dashboard/InstitutionalDashboardClient"
    ).then((m) => ({ default: m.InstitutionalDashboardClient })),
  {
    ssr: false,
    loading: () => (
      <div
        className="space-y-4 p-2"
        role="status"
        aria-live="polite"
        aria-label="Loading research panels"
      >
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-16 w-full" />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <Skeleton className="h-48 w-full" />
      </div>
    ),
  },
);

export default function InstitutionalStandardsDashboardPage() {
  return <InstitutionalDashboardClient />;
}
