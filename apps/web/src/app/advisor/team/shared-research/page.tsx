"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";
import { SharedResearchWorkspace } from '../../../../components/advisor/SharedResearch';


const SharedResearchWorkspace = dynamic(
  () =>
    import("@/components/advisor/SharedResearch").then(
      (m) => m.SharedResearchWorkspace,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function TeamSharedResearchPage() {
  return <SharedResearchWorkspace />;
}
