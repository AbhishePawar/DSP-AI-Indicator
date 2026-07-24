"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const AdvisorResearchNotesWorkspace = dynamic(
  () =>
    import("@/components/advisor/AdvisorResearch").then((m) => m.AdvisorResearchNotesWorkspace),
  {
    loading: () => <Skeleton className="h-64 w-full" />,
    ssr: false,
  },
);

export default function AdvisorResearchNotesPage() {
  return <AdvisorResearchNotesWorkspace />;
}
