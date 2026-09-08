"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";
import { SharedPortfolioComparePage } from '../../../../../components/advisor/SharedPortfolio';


const SharedPortfolioComparePage = dynamic(
  () =>
    import("@/components/advisor/SharedPortfolio").then(
      (m) => m.SharedPortfolioComparePage,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function SharedPortfolioCompareRoute() {
  return <SharedPortfolioComparePage />;
}
