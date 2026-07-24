"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const SharedResearchActivityPage = dynamic(
  () =>
    import("@/components/advisor/SharedResearch").then(
      (m) => m.SharedResearchActivityPage,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function SharedResearchActivityRoute() {
  return <SharedResearchActivityPage />;
}
