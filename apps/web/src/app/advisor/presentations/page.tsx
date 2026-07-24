"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const PresentationWorkspace = dynamic(
  () =>
    import("@/components/advisor/AdvisorPresentation").then((m) => m.PresentationWorkspace),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function AdvisorPresentationsPage() {
  return <PresentationWorkspace />;
}
