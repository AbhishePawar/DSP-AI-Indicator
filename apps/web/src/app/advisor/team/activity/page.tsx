"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";
import { ActivitySection } from '../../../../components/advisor/TeamCollaboration';


const ActivitySection = dynamic(
  () =>
    import("@/components/advisor/TeamCollaboration").then((m) => m.ActivitySection),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function TeamActivityPage() {
  return <ActivitySection />;
}
