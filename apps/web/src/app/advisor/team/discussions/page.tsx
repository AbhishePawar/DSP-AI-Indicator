"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const DiscussionsSection = dynamic(
  () =>
    import("@/components/advisor/TeamCollaboration").then(
      (m) => m.DiscussionsSection,
    ),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function TeamDiscussionsPage() {
  return <DiscussionsSection />;
}
