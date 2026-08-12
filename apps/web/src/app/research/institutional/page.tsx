"use client";

/**
 * Institutional Research Reports — publishing workspace.
 * RC3-004 — dynamic import + skeleton loading.
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

import { Skeleton } from "@/components/ds";

function ReportsFallback() {
  return (
    <div
      className="space-y-3 p-4"
      role="status"
      aria-live="polite"
      aria-label="Loading institutional research reports"
    >
      <Skeleton className="h-10 w-80" />
      <Skeleton className="h-16 w-full" />
      <Skeleton className="h-64 w-full" />
      <p className="text-sm text-[var(--muted)]">
        Loading institutional research reports workspace…
      </p>
    </div>
  );
}

const InstitutionalReportsWorkspace = dynamic(
  () =>
    import("@/components/institutional-reports").then((m) => ({
      default: m.InstitutionalReportsWorkspace,
    })),
  {
    ssr: false,
    loading: () => <ReportsFallback />,
  },
);

export default function InstitutionalResearchReportsPage() {
  return (
    <Suspense fallback={<ReportsFallback />}>
      <InstitutionalReportsWorkspace />
    </Suspense>
  );
}
