"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";
import { AdvisorResearchTimelineWorkspace } from '../../../../components/advisor/AdvisorResearch';


const AdvisorResearchTimelineWorkspace = dynamic(
  () =>
    import("@/components/advisor/AdvisorResearch").then(
      (m) => m.AdvisorResearchTimelineWorkspace,
    ),
  {
    loading: () => <Skeleton className="h-64 w-full" />,
    ssr: false,
  },
);

export default function AdvisorResearchTimelinePage() {
  return <AdvisorResearchTimelineWorkspace />;
}
