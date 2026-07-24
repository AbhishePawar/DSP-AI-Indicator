"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const AdvisorWorkspace = dynamic(
  () =>
    import("@/components/advisor/AdvisorWorkspace").then((m) => m.AdvisorWorkspace),
  {
    loading: () => (
      <div className="space-y-3" aria-busy="true" aria-label="Loading advisor workspace">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    ),
    ssr: false,
  },
);

export default function AdvisorPage() {
  return <AdvisorWorkspace />;
}
