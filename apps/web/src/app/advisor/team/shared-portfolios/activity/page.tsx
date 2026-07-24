"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const SharedPortfolioActivityPage = dynamic(
  () =>
    import("@/components/advisor/SharedPortfolio").then(
      (m) => m.SharedPortfolioActivityPage,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function SharedPortfolioActivityRoute() {
  return <SharedPortfolioActivityPage />;
}
