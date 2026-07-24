"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const CollaborationValidationPage = dynamic(
  () =>
    import("@/components/advisor/CollaborationDashboard").then(
      (m) => m.CollaborationValidationPage,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function TeamValidationPage() {
  return <CollaborationValidationPage />;
}
