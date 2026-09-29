"use client";

/**
 * /advisor — Figma Make `Advisor.tsx` (client book on /api/v1/advisor/clients).
 * The former demo-data advisor workspace and its sub-routes were retired.
 */

import dynamic from "next/dynamic";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Skeleton } from "@/components/ds";

const AdvisorClients = dynamic(
  () => import("@/components/pages").then((m) => ({ default: m.AdvisorClients })),
  {
    ssr: false,
    loading: () => (
      <div className="space-y-4 py-6" role="status" aria-label="Loading advisor">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    ),
  },
);

export default function AdvisorPage() {
  return (
    <ProtectedRoute>
      <AdvisorClients />
    </ProtectedRoute>
  );
}
