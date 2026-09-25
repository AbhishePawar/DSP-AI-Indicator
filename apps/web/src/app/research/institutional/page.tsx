"use client";

/**
 * Institutional — Figma Make `InstitutionalResearch.tsx` (coverage stats ·
 * Quality Screener · Coverage Growth · Rating Distribution). No universe
 * screener or coverage feed exists on /api/v1, so those tiles are honest
 * unavailable states; screener rows are this session's backend analyses.
 * RC3-004 — dynamic import + skeleton for route code-splitting.
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

import { Skeleton } from "@/components/ds";

function InstitutionalFallback() {
  return (
    <div
      className="space-y-5 py-6"
      role="status"
      aria-live="polite"
      aria-label="Loading Institutional Research"
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
      </div>
      <div className="grid gap-5 lg:grid-cols-[1fr_280px]">
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    </div>
  );
}

const InstitutionalResearch = dynamic(
  () => import("@/components/pages").then((m) => ({ default: m.InstitutionalResearch })),
  { ssr: false, loading: () => <InstitutionalFallback /> },
);

export default function InstitutionalResearchPage() {
  return (
    <Suspense fallback={<InstitutionalFallback />}>
      <InstitutionalResearch />
    </Suspense>
  );
}
