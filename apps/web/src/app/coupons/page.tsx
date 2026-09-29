"use client";

/**
 * /coupons — Figma Make `Coupons.tsx` over administrator-provisioned coupon
 * metadata (`GET /api/v1/saas/coupons`). Nothing is invented.
 */

import dynamic from "next/dynamic";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Skeleton } from "@/components/ds";

const CouponsOffers = dynamic(
  () => import("@/components/pages").then((m) => ({ default: m.CouponsOffers })),
  {
    ssr: false,
    loading: () => (
      <div className="space-y-4 py-6" role="status" aria-label="Loading offers">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    ),
  },
);

export default function CouponsPage() {
  return (
    <ProtectedRoute>
      <CouponsOffers />
    </ProtectedRoute>
  );
}
