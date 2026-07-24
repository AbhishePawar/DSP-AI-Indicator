"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const SharedPortfolioDiscussionPage = dynamic(
  () =>
    import("@/components/advisor/SharedPortfolio").then(
      (m) => m.SharedPortfolioDiscussionPage,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function SharedPortfolioDiscussionRoute() {
  return <SharedPortfolioDiscussionPage />;
}
