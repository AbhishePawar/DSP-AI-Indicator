"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const PortfolioNotesWorkspace = dynamic(
  () =>
    import("@/components/advisor/ModelPortfolioManager").then(
      (m) => m.PortfolioNotesWorkspace,
    ),
  {
    loading: () => <Skeleton className="h-64 w-full" />,
    ssr: false,
  },
);

export default function AdvisorPortfolioNotesPage() {
  return <PortfolioNotesWorkspace />;
}
