"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";
import { SharedPortfolioScenariosPage } from '../../../../../components/advisor/SharedPortfolio';


const SharedPortfolioScenariosPage = dynamic(
  () =>
    import("@/components/advisor/SharedPortfolio").then(
      (m) => m.SharedPortfolioScenariosPage,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function SharedPortfolioScenariosRoute() {
  return <SharedPortfolioScenariosPage />;
}
