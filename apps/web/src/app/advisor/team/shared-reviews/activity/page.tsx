"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const TeamReviewActivityPage = dynamic(
  () =>
    import("@/components/advisor/SharedTeamReview").then(
      (m) => m.TeamReviewActivityPage,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function TeamReviewActivityRoute() {
  return <TeamReviewActivityPage />;
}
