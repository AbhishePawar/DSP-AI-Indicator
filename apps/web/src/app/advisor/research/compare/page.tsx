"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const CompareWorkspace = dynamic(
  () => import("@/components/advisor/AdvisorResearch").then((m) => m.CompareWorkspace),
  {
    loading: () => <Skeleton className="h-64 w-full" />,
    ssr: false,
  },
);

export default function AdvisorResearchComparePage() {
  return <CompareWorkspace />;
}
