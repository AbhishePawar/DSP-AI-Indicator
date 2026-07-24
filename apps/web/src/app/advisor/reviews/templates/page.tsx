"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const ReviewTemplatesWorkspace = dynamic(
  () =>
    import("@/components/advisor/ClientReview").then((m) => m.ReviewTemplatesWorkspace),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function AdvisorReviewTemplatesPage() {
  return <ReviewTemplatesWorkspace />;
}
