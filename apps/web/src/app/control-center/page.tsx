"use client";

/**
 * /control-center — Figma Make `ControlCenter.tsx`: the signed-in user's
 * settings (account · notifications · research preferences · interface ·
 * danger zone). The Super Admin platform console lives at
 * /admin/control-center.
 */

import dynamic from "next/dynamic";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Skeleton } from "@/components/ds";

const ControlCenterSettings = dynamic(
  () => import("@/components/pages").then((m) => ({ default: m.ControlCenterSettings })),
  {
    ssr: false,
    loading: () => (
      <div className="space-y-4 py-6" role="status" aria-label="Loading settings">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    ),
  },
);

export default function ControlCenterPage() {
  return (
    <ProtectedRoute>
      <ControlCenterSettings />
    </ProtectedRoute>
  );
}
