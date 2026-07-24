"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const ResearchLibraryWorkspace = dynamic(
  () =>
    import("@/components/advisor/AdvisorResearch").then((m) => m.ResearchLibraryWorkspace),
  {
    loading: () => <Skeleton className="h-64 w-full" />,
    ssr: false,
  },
);

export default function AdvisorResearchPage() {
  return <ResearchLibraryWorkspace />;
}
