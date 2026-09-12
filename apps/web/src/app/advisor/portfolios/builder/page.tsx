"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";
import { PortfolioBuilderWorkspace } from '../../../../components/advisor/ModelPortfolioManager';


const PortfolioBuilderWorkspace = dynamic(
  () =>
    import("@/components/advisor/ModelPortfolioManager").then(
      (m) => m.PortfolioBuilderWorkspace,
    ),
  {
    loading: () => <Skeleton className="h-64 w-full" />,
    ssr: false,
  },
);

export default function AdvisorPortfolioBuilderPage() {
  return <PortfolioBuilderWorkspace />;
}
