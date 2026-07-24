"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const MeetingsWorkspace = dynamic(
  () =>
    import("@/components/advisor/AdvisorWorkspace").then((m) => m.MeetingsWorkspace),
  {
    loading: () => <Skeleton className="h-64 w-full" />,
    ssr: false,
  },
);

export default function AdvisorMeetingsPage() {
  return <MeetingsWorkspace />;
}
