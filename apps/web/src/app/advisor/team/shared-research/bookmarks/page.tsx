"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const SharedResearchBookmarksPage = dynamic(
  () =>
    import("@/components/advisor/SharedResearch").then(
      (m) => m.SharedResearchBookmarksPage,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function SharedResearchBookmarksRoute() {
  return <SharedResearchBookmarksPage />;
}
