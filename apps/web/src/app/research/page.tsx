"use client";

/**
 * Research Hub — Figma Make `ResearchHub.tsx` (Start new research · Saved
 * Research · Research Templates). Saved research is real /api/v1/analyse
 * session history; no client-side research generation.
 * RC3-004 — dynamic import + skeleton for route code-splitting.
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

import { Skeleton } from "@/components/ds";

function ResearchHubFallback() {
  return (
    <div className="space-y-6 py-6" role="status" aria-live="polite" aria-label="Loading Research Hub">
      <Skeleton className="h-36 w-full" />
      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    </div>
  );
}

const ResearchHub = dynamic(
  () => import("@/components/pages").then((m) => ({ default: m.ResearchHub })),
  { ssr: false, loading: () => <ResearchHubFallback /> },
);

export default function ResearchPage() {
  return (
    <Suspense fallback={<ResearchHubFallback />}>
      <ResearchHub />
    </Suspense>
  );
}
