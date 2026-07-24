"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const SharedResearchComparePage = dynamic(
  () =>
    import("@/components/advisor/SharedResearch").then(
      (m) => m.SharedResearchComparePage,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function SharedResearchCompareRoute() {
  return <SharedResearchComparePage />;
}
