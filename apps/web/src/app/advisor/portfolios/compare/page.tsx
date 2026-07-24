"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const ScenarioComparisonWorkspace = dynamic(
  () =>
    import("@/components/advisor/ModelPortfolioManager").then(
      (m) => m.ScenarioComparisonWorkspace,
    ),
  {
    loading: () => <Skeleton className="h-64 w-full" />,
    ssr: false,
  },
);

export default function AdvisorPortfolioComparePage() {
  return <ScenarioComparisonWorkspace />;
}
