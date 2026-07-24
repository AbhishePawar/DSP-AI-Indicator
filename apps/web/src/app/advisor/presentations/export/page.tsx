"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const PresentationExportWorkspace = dynamic(
  () =>
    import("@/components/advisor/AdvisorPresentation").then(
      (m) => m.PresentationExportWorkspace,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function AdvisorPresentationExportPage() {
  return <PresentationExportWorkspace />;
}
