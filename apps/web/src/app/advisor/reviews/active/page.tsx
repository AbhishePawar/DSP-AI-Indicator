"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const ActiveReviewWorkspace = dynamic(
  () => import("@/components/advisor/ClientReview").then((m) => m.ActiveReviewWorkspace),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function AdvisorActiveReviewPage() {
  return <ActiveReviewWorkspace />;
}
