"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const TeamReviewDiscussionPage = dynamic(
  () =>
    import("@/components/advisor/SharedTeamReview").then(
      (m) => m.TeamReviewDiscussionPage,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function TeamReviewDiscussionRoute() {
  return <TeamReviewDiscussionPage />;
}
