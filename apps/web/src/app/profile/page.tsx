"use client";

/**
 * /profile — Figma Make `ClientProfile.tsx` ("Your Financial Profile" ·
 * Financial Health Score gauge). Data via /api/v1/workspace/profile; the score
 * is computed server-side. The account/security profile that previously
 * rendered here remains available at /profile/account.
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Skeleton } from "@/components/ds";

function ProfileFallback() {
  return (
    <div className="grid gap-6 px-7 py-6 lg:grid-cols-[1fr_360px]" role="status" aria-live="polite" aria-label="Loading financial profile">
      <div className="space-y-4">
        <Skeleton className="h-56 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
      <Skeleton className="h-96 w-full" />
    </div>
  );
}

const ClientProfile = dynamic(
  () => import("@/components/pages").then((m) => ({ default: m.ClientProfile })),
  { ssr: false, loading: () => <ProfileFallback /> },
);

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <Suspense fallback={<ProfileFallback />}>
        <ClientProfile />
      </Suspense>
    </ProtectedRoute>
  );
}
