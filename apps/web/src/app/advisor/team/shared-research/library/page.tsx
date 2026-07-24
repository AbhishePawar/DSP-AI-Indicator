"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const SharedResearchLibraryPage = dynamic(
  () =>
    import("@/components/advisor/SharedResearch").then(
      (m) => m.SharedResearchLibraryPage,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function SharedResearchLibraryRoute() {
  return <SharedResearchLibraryPage />;
}
