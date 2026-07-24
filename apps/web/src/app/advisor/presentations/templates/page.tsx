"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const PresentationTemplatesWorkspace = dynamic(
  () =>
    import("@/components/advisor/AdvisorPresentation").then(
      (m) => m.PresentationTemplatesWorkspace,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function AdvisorPresentationTemplatesPage() {
  return <PresentationTemplatesWorkspace />;
}
