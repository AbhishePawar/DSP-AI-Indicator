"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const TeamReviewProgressPage = dynamic(
  () =>
    import("@/components/advisor/SharedTeamReview").then(
      (m) => m.TeamReviewProgressPage,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function TeamReviewProgressRoute() {
  return <TeamReviewProgressPage />;
}
