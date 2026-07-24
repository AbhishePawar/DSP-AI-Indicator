"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const ClientReviewWorkspace = dynamic(
  () => import("@/components/advisor/ClientReview").then((m) => m.ClientReviewWorkspace),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function AdvisorReviewsPage() {
  return <ClientReviewWorkspace />;
}
