"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";
import { TeamWorkspace } from '../../../components/advisor/TeamCollaboration';


const TeamWorkspace = dynamic(
  () =>
    import("@/components/advisor/TeamCollaboration").then((m) => m.TeamWorkspace),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function TeamCollaborationPage() {
  return <TeamWorkspace />;
}
