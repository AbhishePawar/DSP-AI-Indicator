"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";
import { WorkflowDashboardWorkspace } from '../../../../components/advisor/ClientReview';


const WorkflowDashboardWorkspace = dynamic(
  () =>
    import("@/components/advisor/ClientReview").then((m) => m.WorkflowDashboardWorkspace),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function AdvisorReviewDashboardPage() {
  return <WorkflowDashboardWorkspace />;
}
