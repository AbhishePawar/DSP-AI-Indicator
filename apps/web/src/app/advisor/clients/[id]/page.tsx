"use client";

import dynamic from "next/dynamic";
import { use } from "react";

import { Skeleton } from "@/components/ui/Skeleton";

const ClientDetailWorkspace = dynamic(
  () =>
    import("@/components/advisor/AdvisorWorkspace").then((m) => m.ClientDetailWorkspace),
  {
    loading: () => <Skeleton className="h-64 w-full" />,
    ssr: false,
  },
);

export default function AdvisorClientDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return <ClientDetailWorkspace clientId={id} />;
}
