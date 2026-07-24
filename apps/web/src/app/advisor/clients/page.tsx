"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const ClientsWorkspace = dynamic(
  () =>
    import("@/components/advisor/AdvisorWorkspace").then((m) => m.ClientsWorkspace),
  {
    loading: () => <Skeleton className="h-64 w-full" />,
    ssr: false,
  },
);

export default function AdvisorClientsPage() {
  return <ClientsWorkspace />;
}
