"use client";

/**
 * /diagnostics — Figma Make `Diagnostics.tsx`: overall status · Service
 * Status from `GET /api/v1/health` · this browser session's client logs.
 */

import dynamic from "next/dynamic";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Skeleton } from "@/components/ds";

const DiagnosticsStatus = dynamic(
  () => import("@/components/pages").then((m) => ({ default: m.DiagnosticsStatus })),
  {
    ssr: false,
    loading: () => (
      <div className="space-y-4 py-6" role="status" aria-label="Loading diagnostics">
        <Skeleton className="h-14 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    ),
  },
);

export default function DiagnosticsPage() {
  return (
    <ProtectedRoute>
      <DiagnosticsStatus />
    </ProtectedRoute>
  );
}
