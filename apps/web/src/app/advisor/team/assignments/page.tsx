"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";
import { AssignmentsSection } from '../../../../components/advisor/TeamCollaboration';


const AssignmentsSection = dynamic(
  () =>
    import("@/components/advisor/TeamCollaboration").then(
      (m) => m.AssignmentsSection,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function TeamAssignmentsPage() {
  return <AssignmentsSection />;
}
