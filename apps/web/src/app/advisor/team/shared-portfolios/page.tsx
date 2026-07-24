"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const SharedPortfolioWorkspace = dynamic(
  () =>
    import("@/components/advisor/SharedPortfolio").then(
      (m) => m.SharedPortfolioWorkspace,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function TeamSharedPortfoliosPage() {
  return <SharedPortfolioWorkspace />;
}
