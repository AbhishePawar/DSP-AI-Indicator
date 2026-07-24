"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const PresentationPreviewWorkspace = dynamic(
  () =>
    import("@/components/advisor/AdvisorPresentation").then(
      (m) => m.PresentationPreviewWorkspace,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function AdvisorPresentationPreviewPage() {
  return <PresentationPreviewWorkspace />;
}
