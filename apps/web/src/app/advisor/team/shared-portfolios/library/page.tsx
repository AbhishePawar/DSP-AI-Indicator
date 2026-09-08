"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";
import { SharedPortfolioLibraryPage } from '../../../../../components/advisor/SharedPortfolio';


const SharedPortfolioLibraryPage = dynamic(
  () =>
    import("@/components/advisor/SharedPortfolio").then(
      (m) => m.SharedPortfolioLibraryPage,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function SharedPortfolioLibraryRoute() {
  return <SharedPortfolioLibraryPage />;
}
