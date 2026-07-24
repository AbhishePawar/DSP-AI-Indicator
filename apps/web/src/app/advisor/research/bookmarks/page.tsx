"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const AdvisorResearchBookmarksWorkspace = dynamic(
  () =>
    import("@/components/advisor/AdvisorResearch").then(
      (m) => m.AdvisorResearchBookmarksWorkspace,
    ),
  {
    loading: () => <Skeleton className="h-64 w-full" />,
    ssr: false,
  },
);

export default function AdvisorResearchBookmarksPage() {
  return <AdvisorResearchBookmarksWorkspace />;
}
