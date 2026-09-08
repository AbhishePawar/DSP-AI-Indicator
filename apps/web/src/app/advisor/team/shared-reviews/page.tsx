"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";
import { SharedReviewWorkspace } from '../../../../components/advisor/SharedTeamReview';


const SharedReviewWorkspace = dynamic(
  () =>
    import("@/components/advisor/SharedTeamReview").then(
      (m) => m.SharedReviewWorkspace,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function TeamSharedReviewsPage() {
  return <SharedReviewWorkspace />;
}
