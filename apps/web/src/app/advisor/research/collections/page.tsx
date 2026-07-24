"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const ResearchCollectionWorkspace = dynamic(
  () =>
    import("@/components/advisor/AdvisorResearch").then((m) => m.ResearchCollectionWorkspace),
  {
    loading: () => <Skeleton className="h-64 w-full" />,
    ssr: false,
  },
);

export default function AdvisorResearchCollectionsPage() {
  return <ResearchCollectionWorkspace />;
}
