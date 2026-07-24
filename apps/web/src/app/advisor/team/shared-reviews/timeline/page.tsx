"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const TeamReviewTimelinePage = dynamic(
  () =>
    import("@/components/advisor/SharedTeamReview").then(
      (m) => m.TeamReviewTimelinePage,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function TeamReviewTimelineRoute() {
  return <TeamReviewTimelinePage />;
}
