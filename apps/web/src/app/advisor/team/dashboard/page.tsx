"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";
import { CollaborationDashboard } from '../../../../components/advisor/CollaborationDashboard';


const CollaborationDashboard = dynamic(
  () =>
    import("@/components/advisor/CollaborationDashboard").then(
      (m) => m.CollaborationDashboard,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function TeamCollaborationDashboardPage() {
  return <CollaborationDashboard />;
}
