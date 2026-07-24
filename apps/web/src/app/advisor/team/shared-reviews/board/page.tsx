"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const TeamReviewBoardPage = dynamic(
  () =>
    import("@/components/advisor/SharedTeamReview").then(
      (m) => m.TeamReviewBoardPage,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function TeamReviewBoardRoute() {
  return <TeamReviewBoardPage />;
}
