"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const PresentationBuilderWorkspace = dynamic(
  () =>
    import("@/components/advisor/AdvisorPresentation").then(
      (m) => m.PresentationBuilderWorkspace,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function AdvisorPresentationBuilderPage() {
  return <PresentationBuilderWorkspace />;
}
