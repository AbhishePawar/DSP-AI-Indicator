"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const ModelPortfolioLibraryWorkspace = dynamic(
  () =>
    import("@/components/advisor/ModelPortfolioManager").then(
      (m) => m.ModelPortfolioLibraryWorkspace,
    ),
  {
    loading: () => <Skeleton className="h-64 w-full" />,
    ssr: false,
  },
);

export default function AdvisorPortfoliosPage() {
  return <ModelPortfolioLibraryWorkspace />;
}
