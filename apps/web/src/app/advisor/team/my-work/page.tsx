"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const MyWorkSection = dynamic(
  () =>
    import("@/components/advisor/TeamCollaboration").then((m) => m.MyWorkSection),
  { loading: () => <Skeleton className="h-64 w-full" />, ssr: false },
);

export default function TeamMyWorkPage() {
  return <MyWorkSection />;
}
