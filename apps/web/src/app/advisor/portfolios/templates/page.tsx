"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const PortfolioTemplatesWorkspace = dynamic(
  () =>
    import("@/components/advisor/ModelPortfolioManager").then(
      (m) => m.PortfolioTemplatesWorkspace,
    ),
  {
    loading: () => <Skeleton className="h-64 w-full" />,
    ssr: false,
  },
);

export default function AdvisorPortfolioTemplatesPage() {
  return <PortfolioTemplatesWorkspace />;
}
